import httpx

base_gateway = 'http://127.0.0.1:8000'
base_backend = 'http://127.0.0.1:8001'

with httpx.Client(timeout=10.0) as client:
    r = client.get(f'{base_backend}/health')
    print('BACKEND /health', r.status_code, r.text)

    r = client.get(f'{base_gateway}/health')
    print('GATEWAY /health no API key', r.status_code, r.text)

    r = client.post(
        f'{base_gateway}/login',
        json={'username': 'admin', 'password': 'admin'},
        headers={'x-api-key': 'hackathon2026'},
    )
    print('LOGIN', r.status_code, r.text)
    token = r.json().get('access_token') if r.status_code == 200 else None
    print('TOKEN', token)

    headers = {'authorization': f'Bearer {token}', 'x-api-key': 'hackathon2026'} if token else {}

    if token:
        r = client.get(f'{base_gateway}/whoami', headers=headers)
        print('WHOAMI', r.status_code, r.text)

        r = client.get(f'{base_gateway}/metrics', headers=headers)
        print('METRICS', r.status_code, r.text)

        r = client.post(f'{base_gateway}/test-waf', headers=headers, json={'data': 'hello'})
        print('PROXY normal', r.status_code, r.text)

        r = client.post(f'{base_gateway}/test-waf', headers=headers, json={'data': 'union select 1'})
        print('PROXY SQLi', r.status_code, r.text)
    else:
        print('Skipping auth-protected tests due to missing token')

    r = client.get(f'{base_gateway}/')
    print('STATIC', r.status_code, 'content-length=', len(r.text))
