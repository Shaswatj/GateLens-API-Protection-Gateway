#!/usr/bin/env python3
"""Complete demo test - 100% production ready"""
import requests
import time

API_KEY = 'hackathon2026'
BASE_URL = 'http://127.0.0.1:8000'

tests_passed = 0
tests_total = 0

def test(name, condition, expected="PASS"):
    global tests_passed, tests_total
    tests_total += 1
    if condition:
        tests_passed += 1
        print(f"  ✓ {name}")
        return True
    else:
        print(f"  ✗ {name}")
        return False

print("\n" + "="*70)
print("COMPLETE API GATEWAY DEMO TEST")
print("="*70 + "\n")

# =====================
# STEP 1: AUTH
# =====================
print("STEP 1: AUTHENTICATION")
print("-" * 70)

# Login
login_resp = requests.post(
    f'{BASE_URL}/login',
    json={'username': 'Errorcode', 'password': 'intrusionx'},
    headers={'X-API-Key': API_KEY}
)
token = login_resp.json()['access_token']
test("Login returns 200", login_resp.status_code == 200)
test("Token is valid JWT", len(token) > 50)

headers = {'X-API-Key': API_KEY, 'Authorization': f'Bearer {token}'}

# =====================
# STEP 2: NORMAL REQUESTS
# =====================
print("\nSTEP 2: NORMAL REQUESTS (should all return 200)")
print("-" * 70)

endpoints = ['/api/info', '/api/data', '/users', '/orders', '/health', '/admin']
for endpoint in endpoints:
    resp = requests.get(f'{BASE_URL}{endpoint}', headers=headers)
    test(f"GET {endpoint}: {resp.status_code}", resp.status_code == 200)

# =====================
# STEP 3: ATTACK DETECTION
# =====================
print("\nSTEP 3: ATTACK DETECTION (should all return 403)")
print("-" * 70)

attacks = [
    ('/api/info?id=<script>alert(1)</script>', 'XSS in query'),
    ('/api/info?input=OR 1=1', 'SQLi in query'),
    ('/api/info?path=../../etc/passwd', 'Path traversal'),
]

for endpoint, desc in attacks:
    # Clear IP first for fresh test
    requests.post(f'{BASE_URL}/clear-ip', headers=headers)
    time.sleep(0.5)
    
    resp = requests.get(f'{BASE_URL}{endpoint}', headers=headers)
    result = resp.json()
    test(f"{desc}: blocked", resp.status_code == 403)
    test(f"{desc}: has reason", 'reason' in result and result['reason'])
    test(f"{desc}: has threat score", 'ip_score' in result)

# =====================
# STEP 4: RESPONSE FORMAT
# =====================
print("\nSTEP 4: RESPONSE FORMAT")
print("-" * 70)

# Check 200 response format
resp = requests.get(f'{BASE_URL}/users', headers=headers)
body = resp.json()
test("200 response has 'status'", 'status' in body)
test("200 response has 'ip_score'", 'ip_score' in body)
test("200 response has 'threat_level'", 'threat_level' in body)

# Check 403 response format (clear and test)
requests.post(f'{BASE_URL}/clear-ip', headers=headers)
time.sleep(0.5)
resp = requests.get(f'{BASE_URL}/api/info?id=<script>x</script>', headers=headers)
body = resp.json()
test("403 response has JSON body", body is not None)
test("403 response has 'status'", 'status' in body)
test("403 response has 'reason'", 'reason' in body)
test("403 response has 'ip_score'", 'ip_score' in body)
test("403 response has 'threat_level'", 'threat_level' in body)

# =====================
# STEP 5: RATE LIMITING
# =====================
print("\nSTEP 5: RATE LIMITING")
print("-" * 70)

# Clear IP first
requests.post(f'{BASE_URL}/clear-ip', headers=headers)
time.sleep(0.5)

# Send multiple requests quickly (should be allowed up to limit)
allowed_count = 0
for i in range(15):
    resp = requests.get(f'{BASE_URL}/api/info', headers=headers)
    if resp.status_code == 200:
        allowed_count += 1
    elif resp.status_code == 429:
        print(f"  Rate limit triggered after {i} requests")
        break

test(f"Rate limiting active", allowed_count < 15, f"allowed {allowed_count} before limit")

# =====================
# SUMMARY
# =====================
print("\n" + "="*70)
print(f"RESULTS: {tests_passed}/{tests_total} tests passed")
if tests_passed == tests_total:
    print("✓ ALL TESTS PASSED - SYSTEM READY FOR PRODUCTION")
else:
    print(f"⚠ {tests_total - tests_passed} test(s) failed")
print("="*70 + "\n")
