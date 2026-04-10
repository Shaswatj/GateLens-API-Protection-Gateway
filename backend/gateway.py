import json
import time
from collections import deque
from typing import Any, Dict, Optional

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from auth import LoginRequest, authenticate_jwt, create_access_token, validate_api_key
from metrics import (
    get_metrics,
    record_alert,
    record_attack_types,
    record_block,
    record_block_reason,
    record_ip_request,
    record_request,
    record_user_request,
)
from security.engine import evaluate_request

PUBLIC_PATHS = {'/login', '/docs', '/openapi.json'}

app = FastAPI(title='Secure API Gateway')


@app.middleware('http')
async def public_route_middleware(request: Request, call_next):
    if request.url.path in PUBLIC_PATHS:
        return await call_next(request)
    return await call_next(request)

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
            detail={'status': 'blocked', 'score': 0, 'reasons': ['input_size']},
        )
    if len(request.url.path) > MAX_PATH_LENGTH or len(request.url.query) > MAX_QUERY_LENGTH:
        record_block_reason('input_size')
        record_block()
        raise HTTPException(
            status_code=413,
            detail={'status': 'blocked', 'score': 0, 'reasons': ['input_size']},
        )


def _raise_block(reason: str, status_code: int = 403) -> None:
    record_block_reason(reason)
    record_block()
    raise HTTPException(
        status_code=status_code,
        detail={'status': 'blocked', 'score': 0, 'reasons': [reason]},
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
            detail={'status': 'blocked', 'score': 0, 'reasons': ['rate_limit']},
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
                detail={'status': 'blocked', 'score': 0, 'reasons': ['rate_limit']},
            )


@app.post('/login')
async def login(request: LoginRequest):
    if request.username == 'admin' and request.password == 'admin':
        token = create_access_token({'user_id': 1, 'role': 'admin'})
        return {'access_token': token, 'token_type': 'bearer'}

    if request.username == 'user' and request.password == 'user':
        token = create_access_token({'user_id': 2, 'role': 'user'})
        return {'access_token': token, 'token_type': 'bearer'}

    raise HTTPException(status_code=401, detail='Invalid credentials')


@app.get('/metrics')
async def metrics(x_api_key: str = Depends(validate_api_key), token_payload: dict = Depends(authenticate_jwt)):
    return get_metrics()


@app.api_route('/{path:path}', methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'])
async def gateway(path: str, request: Request, api_key: Any = Depends(validate_api_key), token_payload: dict = Depends(authenticate_jwt)):
    body = await request.body()
    user_id = token_payload.get('user_id')
    role = token_payload.get('role')
    record_request()
    record_user_request(user_id)

    _validate_input_size(request, body)

    requested_id = _extract_user_id_from_query(request)
    path_target_id = _get_path_target_id(path)

    if path.startswith('users') and requested_id and str(user_id) != requested_id:
        _raise_block('bola')

    if path.startswith('users') and path_target_id and str(user_id) != path_target_id:
        _raise_block('bola')

    if _is_admin_route(request.url.path) and role != 'admin':
        _raise_block('rbac')

    if _is_json_request(request) and not _validate_json_body(body):
        _raise_block('invalid_json')

    if _has_mass_assignment(request, body):
        _raise_block('mass_assignment')

    result = evaluate_request(request, body, token_payload)

    if result['status'] == 'block':
        record_block_reason('attack')
        record_attack_types(result['reasons'])
        raise HTTPException(status_code=403, detail={'status': 'blocked', 'score': result['score'], 'reasons': result['reasons']})

    if result['status'] == 'alert':
        record_alert()
        record_attack_types(result['reasons'])

    _enforce_rate_limit(request, user_id)

    return JSONResponse(
        status_code=200,
        content={
            'status': result['status'],
            'score': result['score'],
            'reasons': result['reasons'],
            'path': path,
            'message': 'Request processed',
        },
    )
