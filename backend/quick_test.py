#!/usr/bin/env python3
"""Quick diagnostic test"""
import requests
import json

API_KEY = 'hackathon2026'
BASE_URL = 'http://127.0.0.1:8000'

print('=== TESTING AUTH FLOW ===\n')

# Step 1: Login
print('1. Login...')
try:
    login_response = requests.post(
        f'{BASE_URL}/login',
        json={'username': 'Errorcode', 'password': 'intrusionx'},
        headers={'X-API-Key': API_KEY},
        timeout=5
    )
    print(f'   Status: {login_response.status_code}')
    if login_response.status_code == 200:
        token = login_response.json()['access_token']
        print(f'   ✓ Token obtained\n')
    else:
        print(f'   ✗ Error: {login_response.text}\n')
        exit(1)
except Exception as e:
    print(f'   ✗ Connection failed: {e}\n')
    exit(1)

# Step 2: Normal request
print('2. Normal request to /api/info...')
headers = {
    'X-API-Key': API_KEY,
    'Authorization': f'Bearer {token}'
}
response = requests.get(f'{BASE_URL}/api/info', headers=headers)
print(f'   Status: {response.status_code}')
if response.status_code == 200:
    print(f'   ✓ Request succeeded')
else:
    print(f'   ✗ Failed: {response.text[:100]}')

# Step 3: /users endpoint
print('\n3. Request to /users...')
response = requests.get(f'{BASE_URL}/users', headers=headers)
print(f'   Status: {response.status_code}')
if response.status_code == 200:
    print(f'   ✓ Users endpoint works')
else:
    print(f'   ✗ Failed: {response.text[:100]}')

# Step 4: XSS attack
print('\n4. XSS attack test...')
response = requests.get(f'{BASE_URL}/api/user?id=<script>alert(1)</script>', headers=headers)
print(f'   Status: {response.status_code}')
if response.status_code == 403:
    print(f'   ✓ XSS correctly blocked')
    print(f'   Response: {response.json()}')
else:
    print(f'   ✗ Not blocked, status={response.status_code}')

# Step 5: SQLi attack
print('\n5. SQLi attack test...')
response = requests.get(f'{BASE_URL}/api/user?id=OR%201=1', headers=headers)
print(f'   Status: {response.status_code}')
if response.status_code == 403:
    print(f'   ✓ SQLi correctly blocked')
else:
    print(f'   Response: {response.text[:100]}')
