# Step-by-Step Verification Test

## PRE-TEST CHECKLIST
- [ ] Backend running on http://127.0.0.1:8001
- [ ] Frontend accessible (open index.html or serve on http://127.0.0.1:8000)
- [ ] Browser DevTools open (F12)
- [ ] Network tab visible to capture requests

---

## TEST 1: LOGIN WITH ADMIN CREDENTIALS

### Expected: Overlay disappears, dashboard loads, no console errors

**Action:**
1. Go to http://127.0.0.1:8000 (or wherever frontend is)
2. Open DevTools Console tab (F12 → Console)
3. Enter credentials: admin / password
4. Click "Sign In" button

**Verify Console Output (should see all these in order):**
```
[LOGIN] Token saved for user: admin | Token length: XXX
[LOGIN] Loading dashboard data...
[FETCH] Metrics response not ok: 200  ← This might appear if status is not ok
[LOGIN] Dashboard data loaded successfully
```

**Verify No Errors in Console:**
- Should NOT see: "Uncaught TypeError", "SyntaxError", etc.
- Should NOT see: "failed to fetch", "401", etc.

### Verify Network Tab:
**POST /login request:**
- Status: 200
- Response: `{access_token: "eyJhbGciOiJIUzI1NiIs...", token_type: "bearer"}`

**GET /metrics request:**
- Status: 200
- Headers include:
  - Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
  - X-API-Key: hackathon2026

### Verify UI:
- [ ] Login overlay is GONE
- [ ] Dashboard is VISIBLE with metrics
- [ ] Auth Status panel shows:
  - User: admin ✓
  - Token: Valid (green badge) ✓
  - API Key: Valid (green badge) ✓

---

## TEST 2: VERIFY TOKEN IN LOCALSTORAGE

**In DevTools Console, run:**
```javascript
console.log("Token:", localStorage.getItem('gatelens_access_token'));
console.log("User:", localStorage.getItem('gatelens_user'));
```

**Expected output:**
```
Token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...  (long JWT string)
User: {"user":"admin","role":"admin"}
```

---

## TEST 3: PAGE REFRESH

**Action:**
1. After login succeeds, press F5 (refresh page)
2. Wait 2 seconds

**Verify:**
- [ ] Login overlay does NOT appear
- [ ] Dashboard loads with same data
- [ ] Metrics are updated

**Console should show:**
```
[RESTORE] Session restored successfully
```

---

## TEST 4: LOGOUT

**Action:**
1. Click "Logout" button (top right)

**Verify:**
- [ ] Login overlay appears
- [ ] All metrics cleared/reset
- [ ] Token removed from localStorage

**Console should show:**
```
Logged out. Please sign in again.
```

---

## TEST 5: INVALID CREDENTIALS

**Action:**
1. Try to login with: admin / wrongpassword

**Verify:**
- [ ] Request fails with status 401
- [ ] Error message shown in login panel
- [ ] Overlay stays visible
- [ ] No token saved to localStorage

**Error message should say:**
```
Login failed 401: Invalid credentials
```

---

## TEST 6: WRONG API KEY (Advanced)

**Action (in DevTools Console):**
```javascript
// Temporarily change API key
const originalKey = localStorage.getItem('api-key') || 'hackathon2026';
// Make a request with wrong key
await fetch('http://127.0.0.1:8001/metrics', {
  headers: {
    'X-API-Key': 'wrong-key',
    'Authorization': 'Bearer ' + localStorage.getItem('gatelens_access_token')
  }
});
```

**Expected:**
- Status: 401
- Response: Invalid API key

---

## TEST 7: POLLING CONTINUES

**Action:**
1. After successful login, wait 5 seconds without doing anything
2. Check Network tab for repeated requests

**Verify:**
- [ ] /metrics is called every 3 seconds
- [ ] /alerts is called every 5 seconds
- [ ] /waf-alerts is called every 5 seconds
- [ ] All have 200 status
- [ ] Metrics values update on dashboard

---

## TEST 8: METRICS API RETURNS DATA CORRECTLY

**In DevTools Console, after login:**
```javascript
const response = await fetch('http://127.0.0.1:8001/metrics', {
  headers: getAuthHeaders ? getAuthHeaders() : {
    'Authorization': 'Bearer ' + localStorage.getItem('gatelens_access_token'),
    'X-API-Key': 'hackathon2026'
  }
});
const data = await response.json();
console.log(data);
```

**Verify response has:**
- [ ] total_requests (number)
- [ ] total_blocked (number)
- [ ] avg_response_time_ms (number)
- [ ] requests_this_minute (number)
- [ ] rate_limit (number)
- [ ] logs (array)

---

## TEST 9: AUTHORIZATION HEADER SENT CORRECTLY

**Action:**
1. In Network tab, right-click on /metrics request
2. Select "Copy as cURL"
3. Paste into a text editor

**Verify curl command includes:**
```bash
-H 'Authorization: Bearer eyJhbGciOiJIUzI1Ni...'
-H 'X-API-Key: hackathon2026'
```

**Note: The Bearer token should be the JWT string**

---

## TEST 10: TIME ZONE / EXPIRY CHECK

**In DevTools Console:**
```javascript
const token = localStorage.getItem('gatelens_access_token');
const parts = token.split('.');
const decoded = JSON.parse(atob(parts[1]));
console.log('Token expires at:', new Date(decoded.exp * 1000));
console.log('Current time:', new Date());
console.log('Token valid:', decoded.exp * 1000 > Date.now());
```

**Expected:**
- Token expiry should be 60 minutes in the future (or whatever config says)
- Token valid should be: true

---

## DEBUGGING IF TESTS FAIL

### If login overlay doesn't disappear:
1. Check Console for error messages
2. Check Network tab - did /login return 200?
3. Check if response has `access_token` field
4. Check if `saveSession()` was called:
   ```javascript
   console.log(localStorage.getItem('gatelens_access_token')); // Should have token
   ```

### If 401 on /metrics:
1. Check Console: Look for JWT_ERROR in backend logs
2. Check token format:
   ```javascript
   const token = localStorage.getItem('gatelens_access_token');
   console.log('Token length:', token?.length); // Should be ~100+ chars
   console.log('Token starts with:', token?.substring(0, 20));
   ```
3. Check Authorization header sent:
   ```javascript
   // Open Network tab, click /metrics, look under Headers
   // Should see: Authorization: Bearer <token>
   ```

### If metrics don't update:
1. Check Network tab for polling requests
2. Verify they have correct headers
3. Check response status codes
4. Check backend logs for errors

### If page refresh loses session:
1. Check localStorage still has token:
   ```javascript
   localStorage.getItem('gatelens_access_token') // Should not be null
   ```
2. Check if /restore-session or first /metrics call returns 200
3. Check Console for [RESTORE] logs

---

## FINAL VERIFICATION CHECKLIST

After all tests pass:
- [ ] Login works with correct credentials
- [ ] Login fails with wrong credentials
- [ ] Overlay disappears on successful login
- [ ] Dashboard loads with data
- [ ] Token saved to localStorage
- [ ] Token has Bearer prefix in Authorization header
- [ ] Token is still valid after page refresh
- [ ] Metrics polling continues every 3-5 seconds
- [ ] Logout clears session and shows login overlay
- [ ] No random 401 errors
- [ ] No console errors or warnings
- [ ] UI is stable and responsive

**If all checks pass: System is working correctly ✓**

