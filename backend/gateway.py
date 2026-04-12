import json
import time
from collections import deque
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from auth import LoginRequest, authenticate_jwt, create_access_token, validate_api_key
from core.decision import evaluate_request
from core.metrics import (
    append_log,
    append_waf_block,
    get_alerts_payload,
    get_metrics_payload,
    get_waf_alerts_payload,
    record_allowed_request,
    record_blocked_request,
)
from metrics import (
    record_alert,
    record_attack_types,
    record_block,
    record_block_reason,
    record_ip_request,
)
from security.abuse import abuse as abuse_data
from ml.attack_detector import detector as ml_detector

app = FastAPI(title='Secure API Gateway')

# Custom exception handler for HTTPException to properly serialize dict details to JSON
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if isinstance(exc.detail, dict):
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.detail,
            headers=exc.headers or {}
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={'detail': exc.detail},
        headers=exc.headers or {}
    )

# Initialize ML detector on startup
print(f"[STARTUP] ML detector initialized. Model loaded: {ml_detector.loaded}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

RATE_LIMIT_WINDOW = 60
RATE_LIMIT_MAX_REQUESTS = 100
MAX_BODY_BYTES = 8192
MAX_QUERY_LENGTH = 2048
MAX_PATH_LENGTH = 2048
RATE_LIMIT_STORE: Dict[str, deque] = {}
RATE_LIMIT_USER_STORE: Dict[int, deque] = {}
ALLOWED_FIELDS = {
    'users': {'username', 'email'},
    'profiles': {'username', 'email'},
    'accounts': {'username', 'email'},
}


def _get_client_ip(request: Request) -> str:
    return request.client.host if request.client else 'unknown'


def _is_admin_route(path: str) -> bool:
    normalized = '/' + path.lstrip('/')
    return normalized == '/admin' or normalized.startswith('/admin/')


def _get_resource(path: str) -> str:
    parts = path.strip('/').split('/')
    return parts[0] if parts else ''


def _get_path_target_id(path: str) -> str:
    parts = path.strip('/').split('/')
    if len(parts) >= 2 and parts[0] == 'users':
        return parts[1]
    return ''


def _is_json_request(request: Request) -> bool:
    content_type = request.headers.get('content-type', '').lower()
    return content_type.startswith('application/json')


def _parse_json(body: bytes) -> Optional[Dict[str, Any]]:
    if not body:
        return None
    try:
        return json.loads(body.decode('utf-8'))
    except (ValueError, UnicodeDecodeError):
        return None


def _validate_json_body(body: bytes) -> bool:
    if not body:
        return True
    payload = _parse_json(body)
    return payload is not None


def _has_mass_assignment(request: Request, body: bytes) -> bool:
    if request.method not in {'POST', 'PUT', 'PATCH'} or not _is_json_request(request):
        return False
    payload = _parse_json(body)
    if not isinstance(payload, dict):
        return False
    resource = _get_resource(request.url.path)
    allowed = ALLOWED_FIELDS.get(resource)
    if allowed is None:
        return False
    extra = set(payload.keys()) - allowed
    return bool(extra)


def _extract_user_id_from_query(request: Request) -> str:
    return request.query_params.get('id', '')


def _validate_input_size(request: Request, body: bytes) -> None:
    if len(body) > MAX_BODY_BYTES:
        record_block_reason('input_size')
        record_block()
        raise HTTPException(
            status_code=413,
            detail={'status': 'blocked', 'score': 0, 'reason': 'input_size', 'reasons': ['input_size']},
        )
    if len(request.url.path) > MAX_PATH_LENGTH or len(request.url.query) > MAX_QUERY_LENGTH:
        record_block_reason('input_size')
        record_block()
        raise HTTPException(
            status_code=413,
            detail={'status': 'blocked', 'score': 0, 'reason': 'input_size', 'reasons': ['input_size']},
        )


def _extract_reason(detail: Any) -> str:
    if isinstance(detail, dict):
        if isinstance(detail.get('reason'), str):
            return detail['reason']
        if isinstance(detail.get('reasons'), list) and detail['reasons']:
            return ', '.join(str(r) for r in detail['reasons'])
        if 'detail' in detail:
            return str(detail['detail'])
        return ''
    return str(detail or '')


def _raise_block(reason: str, status_code: int = 403) -> None:
    record_block_reason(reason)
    record_block()
    raise HTTPException(
        status_code=status_code,
        detail={'status': 'blocked', 'score': 0, 'reason': reason, 'reasons': [reason]},
        headers={'X-WAF-Status': 'block', 'X-WAF-Reason': reason},
    )


def _enforce_rate_limit(request: Request, user_id: Optional[int]) -> None:
    client_ip = _get_client_ip(request)
    now = time.time()

    ip_window = RATE_LIMIT_STORE.setdefault(client_ip, deque())
    while ip_window and now - ip_window[0] > RATE_LIMIT_WINDOW:
        ip_window.popleft()
    ip_window.append(now)
    record_ip_request(client_ip)
    if len(ip_window) > RATE_LIMIT_MAX_REQUESTS:
        record_block_reason('rate_limit')
        record_block()
        raise HTTPException(
            status_code=429,
            detail={'status': 'blocked', 'score': 0, 'reason': 'rate_limit', 'reasons': ['rate_limit']},
        )

    if user_id is not None:
        user_window = RATE_LIMIT_USER_STORE.setdefault(user_id, deque())
        while user_window and now - user_window[0] > RATE_LIMIT_WINDOW:
            user_window.popleft()
        user_window.append(now)
        if len(user_window) > RATE_LIMIT_MAX_REQUESTS:
            record_block_reason('rate_limit')
            record_block()
            raise HTTPException(
                status_code=429,
                detail={'status': 'blocked', 'score': 0, 'reason': 'rate_limit', 'reasons': ['rate_limit']},
            )


def _get_request_payload(body: bytes) -> Any:
    parsed = _parse_json(body)
    if parsed is not None:
        return parsed
    try:
        return body.decode('utf-8', errors='ignore')
    except Exception:
        return str(body)


@app.post('/login')
async def login(request: LoginRequest, x_api_key: str = Depends(validate_api_key)):
    if request.username == "Errorcode" and request.password == "intrusionx":
        token = create_access_token({'user_id': 1, 'role': 'admin'})
        print("LOGIN SUCCESS:", request.username)
        return {'access_token': token, 'token_type': 'bearer'}

    raise HTTPException(status_code=401, detail='Invalid credentials')


@app.get('/metrics')
async def metrics(x_api_key: str = Depends(validate_api_key), token_payload: dict = Depends(authenticate_jwt)):
    return get_metrics_payload(abuse_data, rate_limit=RATE_LIMIT_MAX_REQUESTS)


@app.get('/alerts')
async def alerts(x_api_key: str = Depends(validate_api_key), token_payload: dict = Depends(authenticate_jwt)):
    return get_alerts_payload(abuse_data)


@app.get('/waf-alerts')
async def waf_alerts(x_api_key: str = Depends(validate_api_key), token_payload: dict = Depends(authenticate_jwt)):
    return get_waf_alerts_payload(abuse_data)


@app.post('/clear-ip')
async def clear_ip_endpoint(request: Request, x_api_key: str = Depends(validate_api_key), token_payload: dict = Depends(authenticate_jwt)):
    """Clear blocked IP addresses for testing.
    
    Query parameters:
    - ip: Specific IP to clear (optional). If empty, clears all blocked IPs.
    """
    # Import here to avoid circular imports
    from core.state import clear_ip, clear_all_blocked_ips
    
    ip = request.query_params.get('ip', '').strip()
    
    if ip:
        cleared = clear_ip(ip)
        record_block_reason('ip_blacklist_cleared')
        return {
            'status': 'success',
            'action': 'clear_ip',
            'ip': ip,
            'was_blocked': cleared,
            'message': f'IP {ip} cleared' if cleared else f'IP {ip} was not blocked'
        }
    else:
        cleared_count = clear_all_blocked_ips()
        record_block_reason('ip_blacklist_all_cleared')
        return {
            'status': 'success',
            'action': 'clear_all',
            'cleared_count': cleared_count,
            'message': f'Cleared {cleared_count} blocked IPs'
        }


@app.api_route('/{path:path}', methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'])
async def gateway(path: str, request: Request, api_key: Any = Depends(validate_api_key), token_payload: dict = Depends(authenticate_jwt)):
    print(f"DEBUG gateway path={path} method={request.method} token_payload={token_payload} headers={dict(request.headers)}")
    start_time = time.time()
    client_ip = _get_client_ip(request)
    result: Optional[dict] = None
    status_code = 200
    reason = 'ok'

    try:
        body = await request.body()
        print(f"DEBUG gateway body={body!r}")
        user_id = token_payload.get('user_id')
        role = token_payload.get('role')
        print(f"DEBUG gateway user_id={user_id} role={role}")

        _validate_input_size(request, body)
        print("DEBUG gateway input size validated")

        requested_id = _extract_user_id_from_query(request)
        path_target_id = _get_path_target_id(path)
        print(f"DEBUG gateway requested_id={requested_id} path_target_id={path_target_id}")

        if path.startswith('users') and requested_id and str(user_id) != requested_id:
            _raise_block('rbac')

        if path.startswith('users') and path_target_id and str(user_id) != path_target_id:
            _raise_block('rbac')

        if _is_admin_route(request.url.path) and role != 'admin':
            _raise_block('rbac')

        if _is_json_request(request) and not _validate_json_body(body):
            _raise_block('invalid_json')

        if _has_mass_assignment(request, body):
            _raise_block('mass_assignment')

        result = await evaluate_request(request, body, client_ip)
        status = result.get('status', 'allow')
        reason = result.get('reason') or (result.get('reasons', ['ok'])[0] if result.get('reasons') else 'ok')

        if status == 'block':
            record_block_reason(reason)
            record_block()
            record_attack_types(result.get('reasons', []))
            return JSONResponse(
                status_code=403,
                content={
                    'status': 'blocked',
                    'score': result.get('score', 0),
                    'reason': reason,
                    'reasons': result.get('reasons', []),
                    'ip_score': result.get('ip_score', 0),  # NEW: Threat score
                    'threat_level': result.get('threat_level', 'high'),  # NEW: Threat level
                },
                headers={'X-WAF-Status': 'block', 'X-WAF-Reason': reason},
            )

        if status == 'alert':
            record_alert()
            record_attack_types(result.get('reasons', []))

        _enforce_rate_limit(request, user_id)

        response_content = {
            'status': status,
            'score': result.get('score', 0),
            'reason': reason,
            'reasons': result.get('reasons', []),
            'path': path,
            'ip_score': result.get('ip_score', 0),  # NEW: Threat score
            'threat_level': result.get('threat_level', 'low'),  # NEW: Threat level
        }

        if path == 'test-waf':
            response_content['request'] = _get_request_payload(body)
            response_content['message'] = 'WAF test request processed'
        elif path == 'users' and request.method == 'GET':
            response_content['users'] = [
                {'user_id': 1, 'name': 'John Doe', 'email': 'john@example.com'},
                {'user_id': 2, 'name': 'Jane Doe', 'email': 'jane@example.com'},
            ]
        elif path.startswith('users/') and request.method == 'GET':
            if path_target_id.isdigit():
                response_content['user'] = {'user_id': int(path_target_id), 'name': f'User {path_target_id}', 'email': f'user{path_target_id}@example.com'}
            else:
                raise HTTPException(status_code=404, detail='User not found')
        elif path == 'orders' and request.method == 'GET':
            response_content['orders'] = [
                {'id': 1, 'item': 'Laptop', 'price': 999},
                {'id': 2, 'item': 'Smartphone', 'price': 699},
            ]
        elif path == 'admin' and request.method == 'GET':
            response_content['admin'] = {
                'user': 'admin' if role == 'admin' else 'user',
                'role': role,
                'message': 'Admin access granted',
            }
        elif path == 'health':
            response_content['message'] = 'gateway healthy'
        else:
            response_content['message'] = 'Request processed through the gateway'

        response = JSONResponse(status_code=200, content=response_content)
        response.headers['X-WAF-Status'] = status
        response.headers['X-WAF-Reason'] = reason
        return response
    except HTTPException as exc:
        status_code = exc.status_code
        reason = _extract_reason(exc.detail)
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.detail,
            headers={'X-WAF-Status': 'block', 'X-WAF-Reason': reason},
        )
    finally:
        elapsed_ms = int((time.time() - start_time) * 1000)
        log_entry = {
            'time': datetime.utcnow().isoformat(),
            'ip': client_ip,
            'endpoint': request.url.path,
            'method': request.method,
            'status': status_code,
            'reason': reason,
            'response_time_ms': elapsed_ms,
        }
        if status_code >= 400:
            # All 403 responses are WAF blocks by design (security checks in evaluate_request)
            # All other 4xx errors are validation/business logic blocks
            if status_code == 403:
                append_waf_block(log_entry)
            else:
                append_log(log_entry)
            record_blocked_request(elapsed_ms, is_waf=(status_code == 403))
        else:
            append_log(log_entry)
            record_allowed_request(elapsed_ms, alert=(result is not None and result.get('status') == 'alert'))


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=8000)
