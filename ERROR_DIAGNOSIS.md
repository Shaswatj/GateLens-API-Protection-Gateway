# ERROR DIAGNOSIS FLOWCHART

## "LOGIN OVERLAY DOESN'T DISAPPEAR" - Diagnostic Tree

```
START: Click "Sign In" with admin/password
  │
  ├─→ Check: Is there a console error?
  │   ├─ YES → Check error type (see ERROR CODES section)
  │   └─ NO → Continue
  │
  ├─→ Check: Did POST /login request succeed?
  │   ├─ Network tab shows 200 → Continue
  │   ├─ Network tab shows 401 → BAD CREDENTIALS
  │   ├─ Network tab shows error → NETWORK/CORS ERROR
  │   └─ No request at all → FORM HANDLER BUG
  │
  ├─→ Check: Does /login response have access_token?
  │   ├─ YES → Continue
  │   ├─ NO → Response Format Error (see RESPONSE FORMAT ERROR)
  │   └─ Can't see response → Network tab not open
  │
  ├─→ Check: Is token saved to localStorage?
  │   ├─ YES → Continue
  │   ├─ NO → saveSession() not called or validation failed
  │   └─ Check: localStorage.getItem('gatelens_access_token')
  │
  ├─→ Check: Did overlay actually disappear?
  │   ├─ YES → Check: Did it reappear?
  │   │   ├─ YES → 401 on dashboard load (see 401 ON DASHBOARD)
  │   │   └─ NO → ✓ SUCCESS! Check dashboard loads data
  │   ├─ NO → showLoginOverlay(false) might not be called
  │   │   └─ Check: Is showLoginOverlay function working?
  │   │       └─ Try in console: showLoginOverlay(false); then showLoginOverlay(true);
  │   └─ NO CONNECTION → CSS issue? Check display: none/flex
  │
  └─→ CHECK: Dashboard loads data?
      ├─ YES → ✓ ALL SYSTEMS GO!
      └─ NO → See DASHBOARD LOAD ERROR
```

---

## ERROR CODES

### CODE 1: BAD CREDENTIALS (401 from /login)
**Symptom**: Error message shown, overlay stays visible

**Diagnosis**:
- ✓ Form handler working correctly
- ✓ Login function executes
- Problem: Wrong username or password

**Check**:
- Is admin/password correct?
- Has backend been restarted?
- Check backend auth.py lines for valid credentials

**Fix**:
- Use correct credentials: admin/password or user/user
- Restart backend

---

### CODE 2: NETWORK/CORS ERROR (No 200 or 401)
**Symptom**: Request fails with CORS, net::ERR_NAME_NOT_RESOLVED, or timeout

**Diagnosis**:
- Frontend and backend can't communicate

**Check**:
- ✓ Backend running on http://127.0.0.1:8001?
  ```bash
  curl -v http://127.0.0.1:8001/metrics
  ```
- ✓ Frontend accessing correct API_URL?
  - Check: `const API_URL = 'http://127.0.0.1:8001';`
- ✓ CORS configured on backend?
  - Check: `allow_origins=['*']`

**Fix**:
- Start backend: `cd backend && python gateway.py`
- Wait for "Uvicorn running on" message
- Refresh frontend page

---

### CODE 3: RESPONSE FORMAT ERROR (No access_token)
**Symptom**: Error: "Invalid login response: access_token (missing)"

**Diagnosis**:
- Backend returning wrong format

**Check**:
- Look at Network tab → /login response body
- Should be: `{access_token: "JWT...", token_type: "bearer"}`
- Not: `{token: "...", result: {...}}` or other format

**Fix**:
- Check backend /login endpoint:
  ```python
  return {'access_token': token, 'token_type': 'bearer'}
  ```
- Verify gateway.py has this exact code

---

### CODE 4: FORM HANDLER BUG (No request sent)
**Symptom**: Click Sign In, nothing happens, no network request

**Diagnosis**:
- Form submission not being processed

**Check**:
- DevTools Console: Try manually:
  ```javascript
  login('admin', 'password');
  ```
- If that works, form handler isn't attached
- If that fails, login function has issue

**Fix**:
- Check form-form exists: `<form id="login-form">`
- Check form handler:
  ```javascript
  document.getElementById('login-form')?.addEventListener('submit', ...)
  ```
- Ensure bindTestButtons() is called during page load

---

### CODE 5: showLoginOverlay FUNCTION BUG (Overlay won't go away)
**Symptom**: showLoginOverlay(false) doesn't work

**Check**:
- DevTools Console:
  ```javascript
  showLoginOverlay(false);  // Should make overlay disappear
  showLoginOverlay(true);   // Should make it reappear
  ```

**If this doesn't work**:
- CSS issue: Check overlay element styling
  ```javascript
  document.getElementById('login-overlay').style.display  // Should change
  ```

**Fix**:
- Check HTML has:
  ```html
  <div id="login-overlay" class="login-overlay">
    <div class="login-panel">...</div>
  </div>
  ```
- CSS has: `.login-overlay { display: flex/none }`

---

## 401 ON DASHBOARD (Overlay reappears)

If overlay disappears then reappears:

```
Problem: /metrics returning 401 after successful /login

1. Check: Is token really saved?
   localStorage.getItem('gatelens_access_token')
   └─ Should be long JWT string, not null

2. Check: Is Authorization header sent?
   Network tab → /metrics request → Headers
   └─ Should have: Authorization: Bearer <token>

3. Check: Is token valid?
   Decode: const parts = token.split('.');
           JSON.parse(atob(parts[1]))
   └─ Should have: user_id, role, exp

4. Check: Is token expired?
   new Date(decoded.exp * 1000)
   └─ Should be future date

5. Check: Backend JWT processing
   Look at backend console output for:
   - AUTH HEADER: Bearer ...
   - TOKEN: ...
   - DECODED PAYLOAD: {user_id, role, exp}
   - Or JWT ERROR: error message

6. If Backend shows JWT ERROR:
   Possible causes:
   a) SECRET_KEY mismatch
      └─ Check: core/config.py SECRET_KEY = os.getenv("SECRET_KEY", "secret")
      └─ Is .env file overriding with different value?
   
   b) ALGORITHM mismatch
      └─ Check: Both use 'HS256'?
   
   c) Token corrupted in transit
      └─ Check Authorization header format: "Bearer <space> <token>"

7. If Backend shows no error but still 401:
   Check: authenticate_jwt() is being called
   └─ It should print AUTH HEADER and TOKEN lines
```

---

## DASHBOARD LOAD ERROR (Metrics not showing)

If overlay disappears but dashboard shows "No data":

```
Problem: /metrics, /alerts, /waf-alerts returning errors

1. Check: Are the requests being sent?
   Network tab → Filter "XHR"
   └─ Should see GET /metrics, GET /alerts, GET /waf-alerts
   └─ After POST /login

2. Check: Request status
   └─ All should be 200
   └─ If any are 401 → See 401 ON DASHBOARD section
   └─ If any are 500 → Backend error

3. Check: Request headers
   Each request should have:
   - Authorization: Bearer <JWT>
   - X-API-Key: hackathon2026
   - Content-Type: application/json

4. Check: Response body
   Each should have:
   - /metrics: {total_requests, total_blocked, logs, ...}
   - /alerts: {top_abusive_ips: [...]}
   - /waf-alerts: {last_waf_blocks: [...], top_abuse_ips: [...]}

5. Check: Console errors
   Look for:
   - [FETCH] Failed to fetch metrics: TypeError ...
   - → If JSON parse error, response might be HTML error page
   
6. If response is HTML error:
   Backend returned error page instead of JSON
   → Check backend logs for exceptions
   → Restart backend
```

---

## SYSTEMATIC DEBUGGING (Step by Step)

### Step 1: Verify Backend is Running
```bash
# Terminal
curl -v http://127.0.0.1:8001/metrics \
  -H "X-API-Key: hackathon2026" \
  -H "Authorization: Bearer fake"

# Expected: 401 (invalid token)
# Not: Connection refused, timeout, or 404
```

### Step 2: Verify Login Works
```bash
TOKEN=$(curl -s -X POST http://127.0.0.1:8001/login \
  -H "X-API-Key: hackathon2026" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"password"}' \
  | jq -r '.access_token')

echo "Token: $TOKEN"
# Should print: Token: eyJhbGciOiJIUzI1NiIs...
```

### Step 3: Verify Token Works
```bash
curl -v http://127.0.0.1:8001/metrics \
  -H "X-API-Key: hackathon2026" \
  -H "Authorization: Bearer $TOKEN"

# Expected: 200 with JSON data
# Not: 401 or error
```

### Step 4: Test Frontend Locally
```bash
# Open http://127.0.0.1:8000/frontend/index.html
# DevTools Console:
console.log('Test');  # Check console is open

# Now it should show: Test
# Means you can see console output
```

### Step 5: Login Locally
```bash
# Enter admin/password, click Sign In
# Check Console for:
# [LOGIN] Token saved for user: admin | Token length: XXX
# [LOGIN] Loading dashboard data...
# [LOGIN] Dashboard data loaded successfully

# Check localStorage in Console:
localStorage.getItem('gatelens_access_token')
# Should not be null
```

---

## FINAL CHECKLIST

- [ ] Backend console shows no errors
- [ ] Frontend console shows no red errors
- [ ] [LOGIN] messages appear after sign in
- [ ] localStorage has token after login
- [ ] Overlay disappears within 1 second
- [ ] Dashboard shows metrics after 2-3 seconds
- [ ] Polling continues every 3-5 seconds
- [ ] Logout clears session and shows overlay
- [ ] Page refresh doesn't re-ask for login
- [ ] Metrics update on every refresh

**If all checked: System working correctly ✓**

