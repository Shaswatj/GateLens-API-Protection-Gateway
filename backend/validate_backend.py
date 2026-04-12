import http.client
import json

HOST = '127.0.0.1'
PORT = 8001
API_KEY = 'hackathon2026'

conn = http.client.HTTPConnection(HOST, PORT, timeout=10)


def do_request(method, path, headers=None, body=None):
    if headers is None:
        headers = {}
    if body is not None and 'Content-Type' not in headers:
        headers['Content-Type'] = 'application/json'
    if body is not None and isinstance(body, (dict, list)):
        body = json.dumps(body)
    conn.request(method, path, body=body, headers=headers)
    res = conn.getresponse()
    data = res.read().decode('utf-8', errors='replace')
    hdrs = {k: v for k, v in res.getheaders()}
    return res.status, hdrs, data


def print_result(label, status, hdrs, data):
    print(f"{label}: {status}")
    print(f"  X-WAF-Status: {hdrs.get('x-waf-status')} | X-WAF-Reason: {hdrs.get('x-waf-reason')}")
    print(f"  Body: {data}\n")


print('== AUTH TESTS ==')
status, hdrs, data = do_request('POST', '/login', headers={'x-api-key': API_KEY}, body={'username': 'admin', 'password': 'password'})
print_result('LOGIN admin', status, hdrs, data)
admin_token = None
if status == 200:
    admin_token = json.loads(data)['access_token']

status, hdrs, data = do_request('POST', '/login', headers={'x-api-key': API_KEY}, body={'username': 'user', 'password': 'user'})
print_result('LOGIN user', status, hdrs, data)
user_token = None
if status == 200:
    user_token = json.loads(data)['access_token']

print('== API ENDPOINTS ==')
status, hdrs, data = do_request('GET', '/metrics', headers={'x-api-key': API_KEY, 'Authorization': f'Bearer {admin_token}'})
print_result('GET /metrics', status, hdrs, data)

status, hdrs, data = do_request('GET', '/alerts', headers={'x-api-key': API_KEY, 'Authorization': f'Bearer {admin_token}'})
print_result('GET /alerts', status, hdrs, data)

status, hdrs, data = do_request('GET', '/waf-alerts', headers={'x-api-key': API_KEY, 'Authorization': f'Bearer {admin_token}'})
print_result('GET /waf-alerts', status, hdrs, data)

status, hdrs, data = do_request('GET', '/users', headers={'x-api-key': API_KEY, 'Authorization': f'Bearer {admin_token}'})
print_result('GET /users', status, hdrs, data)

status, hdrs, data = do_request('GET', '/admin', headers={'x-api-key': API_KEY, 'Authorization': f'Bearer {admin_token}'})
print_result('GET /admin', status, hdrs, data)

status, hdrs, data = do_request('POST', '/test-waf', headers={'x-api-key': API_KEY, 'Authorization': f'Bearer {admin_token}'}, body={'query': 'normal request'})
print_result('POST /test-waf normal', status, hdrs, data)

print('== ATTACK SIMULATIONS ==')
status, hdrs, data = do_request('POST', '/test-waf', headers={'x-api-key': API_KEY, 'Authorization': f'Bearer {admin_token}'}, body={'query': '1 OR 1=1'})
print_result('POST /test-waf SQLi', status, hdrs, data)

status, hdrs, data = do_request('POST', '/test-waf', headers={'x-api-key': API_KEY, 'Authorization': f'Bearer {admin_token}'}, body={'query': '<script>alert(1)</script>'})
print_result('POST /test-waf XSS', status, hdrs, data)

conn.request('POST', '/test-waf', body='{"query":"bad json"', headers={'Content-Type': 'application/json', 'x-api-key': API_KEY, 'Authorization': f'Bearer {admin_token}'})
res = conn.getresponse()
body = res.read().decode('utf-8', errors='replace')
print_result('POST /test-waf malformed JSON', res.status, {k: v for k, v in res.getheaders()}, body)

status, hdrs, data = do_request('GET', '/admin', headers={'x-api-key': API_KEY, 'Authorization': f'Bearer {user_token}'})
print_result('GET /admin with user token', status, hdrs, data)

print('== RATE LIMIT ==')
limit_status = None
for i in range(105):
    status, hdrs, data = do_request('GET', '/metrics', headers={'x-api-key': API_KEY, 'Authorization': f'Bearer {admin_token}'})
    if status == 429:
        limit_status = (i + 1, status, hdrs.get('x-waf-status'), hdrs.get('x-waf-reason'), data)
        break
print('Rate limit triggered at request', limit_status[0] if limit_status else 'none')
if limit_status:
    print('  status', limit_status[1])
    print('  headers', limit_status[2], limit_status[3])
    print('  body', limit_status[4])

conn.close()
