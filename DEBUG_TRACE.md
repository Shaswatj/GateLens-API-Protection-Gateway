# Complete Auth Flow Debug Trace

## Scenario: User enters admin/password and clicks "Sign In"

### STEP 1: FORM SUBMISSION (Frontend)
```
Event: form submit
Data: {username: "admin", password: "password"}
Handler: bindTestButtons() → login-form.addEventListener('submit', async (event) => {...})

Flow:
1. event.preventDefault()
2. Get formData from form
3. Extract username = "admin", password = "password"
4. Check: if (!username || !password) → FALSE (both present)
5. Call: await login("admin", "password")
```

### STEP 2: LOGIN FUNCTION (Frontend)
```
login("admin", "password"):

1. Clear login error: document.getElementById('login-error').textContent = ''
   Status: ✓ login-error is now empty

2. Call: await apiFetch('/login', {
     method: 'POST',
     includeAuth: false,     ← KEY: No Authorization header
     body: JSON.stringify({username: "admin", password: "password"})
   })

   apiFetch internally:
   - path = "/login" (no change)
   - url = "http://127.0.0.1:8001/login"
   - opts.method = "POST"
   - opts.headers = getAuthHeaders(false) = {
       'Content-Type': 'application/json',
       'X-API-Key': 'hackathon2026'
       // NO Authorization header (includeAuth: false)
     }
   - opts.body = '{"username":"admin","password":"password"}'

   - fetch(url, opts) sends request

3. Response from apiFetch:
   - response.status = 200 OR 401 or error
   
   If response.status === 401:
     - Check: suppressLoginOverlayOn401 = false (default)
     - Execute: clearSession()
     - Execute: showLoginOverlay(true) ← OVERLAY SHOWS
     - Throw error: "Authentication failed. Please log in again."
     
   Otherwise:
     - Return response object

4. After apiFetch returns (assuming response.status = 200):
   - Check: if (!response.ok) → FALSE (200 is ok)
   - Parse: const data = await response.json()
     Expected: {access_token: "JWT_STRING", token_type: "bearer"}
     
   If JSON parse fails:
     - Throw error: stays in memory
     - Error gets caught by form handler
     - Error message displayed
     - Overlay still visible
     ❌ THIS WOULD BE A BUG
     
5. If JSON parse succeeds:
   - data.access_token = "JWT_STRING"
   - Call: saveSession(data.access_token, "admin", "admin")
   
     saveSession internals:
     - accessToken = data.access_token ← JS variable set
     - currentUser = "admin" ← JS variable set
     - currentRole = "admin" ← JS variable set
     - localStorage['gatelens_access_token'] = data.access_token
     - localStorage['gatelens_user'] = '{"user":"admin","role":"admin"}'
     - updateAuthUI() ← Updates UI to show logged-in state
     
   - console.log('[LOGIN] Token saved for user: admin')

6. Call: showLoginOverlay(false)
   - overlay.style.display = 'none'
   ✓ OVERLAY SHOULD BE HIDDEN HERE

7. Call: startPolling()
   - Starts 3 intervals: metrics (3s), alerts (5s), waf (5s)

8. Set flag: suppressLoginOverlayOn401 = true
   - This prevents apiFetch from re-showing overlay if it gets 401

9. Try block:
   - console.log('[LOGIN] Loading dashboard data...')
   
   - await Promise.all([
       fetchDashboard(),    ← Calls apiFetch('/metrics')
       fetchAlerts(),       ← Calls apiFetch('/alerts')
       fetchWAFAlerts()     ← Calls apiFetch('/waf-alerts')
     ])
```

### STEP 3: FETCH DASHBOARD (Frontend → Backend)
```
fetchDashboard():
1. Call: apiFetch('/metrics') with no options
   - Defaults: {method: 'GET', includeAuth: true}
   
   - getAuthHeaders(true) returns:
     {
       'Content-Type': 'application/json',
       'X-API-Key': 'hackathon2026',
       'Authorization': 'Bearer ' + accessToken
       ↑ accessToken was set in saveSession above ✓
     }
   
   - fetch('http://127.0.0.1:8001/metrics', {
       method: 'GET',
       headers: {...}
     })

2. Backend receives /metrics request
   See STEP 4 below
```

### STEP 4: BACKEND /METRICS ENDPOINT
```
Backend:
@app.get('/metrics')
async def metrics(
  x_api_key: str = Depends(validate_api_key),
  token_payload: dict = Depends(authenticate_jwt)
):
  return get_metrics_payload(...)

Dependency chain:

1. validate_api_key() dependency:
   - Receives header: X-API-Key = 'hackathon2026'
   - Check: if x_api_key != 'hackathon2026' → FALSE
   - Returns x_api_key
   Status: ✓ PASS

2. authenticate_jwt() dependency:
   - Receives header: Authorization = 'Bearer JWT_STRING'
   - print('AUTH HEADER:', 'Bearer JWT_STRING')
   - Check: if not authorization → FALSE (header present)
   - Strip: authorization.strip() = 'Bearer JWT_STRING'
   - Check: if not authorization.lower().startswith('bearer ') → FALSE
   - Extract: token = 'JWT_STRING'
   - print('TOKEN:', 'JWT_STRING')
   - Try:
     payload = jwt.decode(
       token='JWT_STRING',
       key=SECRET_KEY,
       algorithms=['HS256']
     )
     ↑ NOTE: SECRET_KEY comes from core.config
     ↑ This must match the key used to create the token!
     
   - If jwt.decode succeeds:
     payload = {
       'user_id': 1,
       'role': 'admin',
       'exp': 1234567890
     }
     print('DECODED PAYLOAD:', payload)
     return payload
     Status: ✓ PASS
     
   - If jwt.decode fails (JWT error):
     print('JWT ERROR:', 'error message')
     Raise HTTPException(status_code=401, detail='Invalid token')
     Result: 401 response sent to frontend ❌

3. If both dependencies pass:
   - Execute: return get_metrics_payload(abuse_data, rate_limit=...)
   - Returns JSON with metrics data

4. Response sent to frontend: 200 with metrics JSON OR 401
```

### STEP 5: CATCH RESPONSE IN FRONTEND
```
Back in fetchDashboard():

1. Response received: 200 OR 401

If response.status === 401:
  - apiFetch detects 401
  - Check: if (!suppressLoginOverlayOn401) → FALSE (flag is true!)
  - Skips: clearSession() and showLoginOverlay(true)
  - Throw error: "Authentication failed. Please log in again."
  - Error caught in try/catch of login() function
  - Error logged: console.error('[LOGIN] Dashboard load error (non-critical):', error)
  - NOT rethrown
  Status: ✓ SUPPRESS CONTROLLED by suppressLoginOverlayOn401

If response.status === 200:
  - Check: if (!response.ok) → FALSE (200 is ok)
  - Parse: const data = await response.json()
  - Populate UI with data
  - Status: ✓ PASS

2. After all 3 Promise.all calls complete (or error):
   - Catch any errors from fetchDashboard/fetchAlerts/fetchWAFAlerts
   - Log error: console.error('[LOGIN] Dashboard load error (non-critical):', error)
   - Do NOT rethrow
   Status: ✓ No errors propagate

3. Finally block:
   - suppressLoginOverlayOn401 = false
   - Reset flag for normal operation

4. After login() completes normally:
   - No error caught by form handler
   - Error message stays empty
   - Overlay is hidden (from step 2/6 above)
   Status: ✓ OVERLAY HIDDEN

5. Form submit handler completes:
   - login() promise resolved
   - No catch block executed
   - Form remains submitted (prevented default)
   Status: ✓ COMPLETE
```

---

## Expected Result: ✓ LOGIN SHOULD WORK

### On Success:
- ✓ Overlay disappears
- ✓ Token saved to localStorage
- ✓ Dashboard loads with metrics
- ✓ Auth UI shows "User: admin", Token: Valid
- ✓ No console errors

### If Issues Occur:

**Issue 1: Overlay doesn't disappear**
- Cause: showLoginOverlay(false) not called OR called but display hidden by CSS
- Debug: Check if response.ok === true after /login

**Issue 2: 401 on /metrics**
- Cause: JWT decode fails
- Debug: Check backend logs for "JWT ERROR"
- Root cause: SECRET_KEY mismatch OR token expired OR malformed token

**Issue 3: Headers missing**
- Cause: getAuthHeaders() not called OR options.includeAuth = false
- Debug: Check Network tab for Authorization header

**Issue 4: Response not JSON**
- Cause: Backend returned HTML error page instead of JSON
- Debug: Check /login response body in Network tab

---

## Critical Configuration to Verify

In `backend/core/config.py`:
```python
SECRET_KEY = os.getenv("SECRET_KEY", "secret")  # ← Match encoding/decoding
ALGORITHM = os.getenv("ALGORITHM", "HS256")       # ← Must be HS256
API_KEY = os.getenv("API_KEY", "hackathon2026")   # ← Match header value
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
```

In `frontend/index.html`:
```javascript
const API_URL = 'http://127.0.0.1:8001';
const API_KEY = 'hackathon2026';  // ← Must match backend
```

---

## Test Commands

### Test 1: Check if backend is running
```bash
curl -X GET http://127.0.0.1:8001/metrics \
  -H "X-API-Key: hackathon2026" \
  -H "Authorization: Bearer missing" \
  -v
# Expected: 401 (missing token is invalid)
```

### Test 2: Full login flow
```bash
# Step 1: Get token
TOKEN=$(curl -X POST http://127.0.0.1:8001/login \
  -H "X-API-Key: hackathon2026" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"password"}' \
  | jq -r '.access_token')

echo "Token: $TOKEN"

# Step 2: Use token to get metrics
curl -X GET http://127.0.0.1:8001/metrics \
  -H "X-API-Key: hackathon2026" \
  -H "Authorization: Bearer $TOKEN" \
  -v
# Expected: 200 with metrics data
```

### Test 3: Check localStorage after login (DevTools Console)
```javascript
localStorage.getItem('gatelens_access_token')
// Should return: "eyJhbGciOiJIUzI1NiIs..." (JWT string)

localStorage.getItem('gatelens_user')
// Should return: '{"user":"admin","role":"admin"}'
```

### Test 4: Check if Authorization header is being sent (Network Tab)
```
In DevTools → Network Tab → Click on /metrics request → Headers
Should see:
  Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
  X-API-Key: hackathon2026
```

---

## Next Diagnosis Steps

1. **Frontend Check**: Open DevTools → Console
   - Click "Sign In" with admin/password
   - Look for console output:
     - `[LOGIN] Token saved for user: admin` ← Should appear
     - `[LOGIN] Loading dashboard data...` ← Should appear
     - `[LOGIN] Dashboard data loaded successfully` ← Should appear
     - Any ERROR messages ← Should NOT appear

2. **Network Check**: Open DevTools → Network Tab
   - Filter by XHR (XMLHttpRequest)
   - Look at /login request:
     - Status: 200
     - Response: {access_token: "JWT", token_type: "bearer"}
   - Look at /metrics request:
     - Status: 200
     - Headers include Authorization: Bearer JWT
     - Response: {total_requests: ..., logs: [...], ...}

3. **Backend Check**: Look at backend console output
   - Should show:
     ```
     AUTH HEADER: Bearer JWT_STRING
     TOKEN: JWT_STRING
     DECODED PAYLOAD: {'user_id': 1, 'role': 'admin', 'exp': ...}
     ```

4. **UI Check**: After login
   - Overlay should be gone
   - Dashboard should show metrics
   - Auth Status should show:
     - User: admin
     - Token: Valid (green)
     - API Key: Valid (green)

---

## If Something is Still Broken

Probable causes in order:
1. **Backend not running** → Start backend: `python backend/gateway.py`
2. **JWT SECRET_KEY mismatch** → Check `.env` file for SECRET_KEY
3. **Frontend token not saved** → Check localStorage after login
4. **Headers not sent** → Check Network tab in DevTools
5. **Response not JSON** → Check response body in Network tab
6. **CORS issues** → Check browser console for CORS errors
7. **Race condition in Promise.all** → Check console logs for timing
8. **Authorization header format wrong** → Should be "Bearer TOKEN", not "bearer TOKEN"

