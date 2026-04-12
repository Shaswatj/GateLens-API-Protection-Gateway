import requests
import time

API_KEY = 'hackathon2026'
URL = 'http://127.0.0.1:8000'

print("\n=== TESTING DECAY AND RECOVERY ===\n")

# Get token first
print("Getting token...")
login = requests.post(
    f'{URL}/login',
    json={'username': 'Errorcode', 'password': 'intrusionx'},
    headers={'X-API-Key': API_KEY}
)
token = login.json()['access_token']
headers = {'X-API-Key': API_KEY, 'Authorization': f'Bearer {token}'}

# Check current score
r = requests.get(f'{URL}/api/info', headers=headers).json()
score_before = r.get('ip_score', 'N/A')
print(f'Current score: {score_before}')

# Wait for decay
print('\nWaiting 12 seconds for score decay...')
for i in range(12):
    time.sleep(1)
    print('.', end='', flush=True)
print()

# Check after decay
r = requests.get(f'{URL}/api/info', headers=headers).json()
score_after_decay = r.get('ip_score', 'N/A')
print(f'Score after decay: {score_after_decay}')
print(f'Threat level: {r.get("threat_level", "N/A")}')

# Test recovery - normal requests should each reduce score by 1
print('\nSending 3 normal requests to test recovery (-1 per request)...')
scores = []
for i in range(3):
    r = requests.get(f'{URL}/api/info', headers=headers).json()
    score = r.get('ip_score', 'N/A')
    scores.append(score)
    print(f'  Request {i+1}: score = {score}')
    time.sleep(1)

if len(scores) >= 2 and isinstance(scores[0], int):
    difference = scores[0] - scores[-1]
    print(f'\nScore decrease: {difference} points (expected ~3)')
    if difference >= 2:
        print('✓ Recovery mechanism working!')
    else:
        print('⚠ Score decrease less than expected')
