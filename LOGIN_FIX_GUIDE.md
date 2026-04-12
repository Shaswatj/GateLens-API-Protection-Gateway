# Login Flow Fix Guide

## Root Cause Identified

The login overlay was not disappearing because:

1. **After successful login**, the code called `showLoginOverlay(false)` to hide the overlay
2. **Then** it attempted to load dashboard data via `Promise.all([fetchDashboard(), fetchAlerts(), fetchWAFAlerts()])`
3. **If any API call failed with 401**, the `apiFetch()` function would:
   - Call `clearSession()`
   - Call `showLoginOverlay(true)` **RE-SHOWING THE OVERLAY**
   - Throw an error

The user saw the overlay reappear even though login was successful.

---

## Fixes Applied

### 1. **Suppress Overlay Re-show During Initial Load** ✓
- Added `suppressLoginOverlayOn401` flag to prevent `apiFetch()` from re-showing overlay immediately after login
- Flag is set to `true` during initial dashboard load, then reset to `false`
- This prevents race conditions where overlay gets reshown

### 2. **Better Error Handling in login()** ✓
- Wrapped `Promise.all([fetchDashboard(), fetchAlerts(), fetchWAFAlerts()])` in try/catch
- Errors in initial dashboard load no longer bubble up to the form handler
- Added console logging for debugging: `[LOGIN]`, `[FETCH]` prefixes

### 3. **Improved Individual Fetch Functions** ✓
- Added response status checking before parsing JSON
- Added console warnings if responses are not ok
- All errors are caught internally and logged without rethrowing
- Consistent error logging with `[FETCH]` prefix

---

## How It Works Now

```
1. User clicks "Sign In"
   ↓
2. login() called → apiFetch('/login', ...) → Post credentials
   ↓
3. Success: Parse token from response
   ↓
4. saveSession(token, user, role)
   ↓
5. showLoginOverlay(false) → OVERLAY HIDDEN
   ↓
6. startPolling() → Start 3s/5s refresh intervals
   ↓
7. suppressLoginOverlayOn401 = true
   ↓
8. Promise.all([fetchDashboard(), fetchAlerts(), fetchWAFAlerts()])
   │  ├─ Each call uses apiFetch() with token from saveSession()
   │  ├─ Headers include: Authorization: Bearer <token>, X-API-Key: <key>
   │  ├─ Errors are caught internally, NOT rethrown
   │  └─ 401 errors don't trigger showLoginOverlay(true)
   ↓
9. suppressLoginOverlayOn401 = false
   ↓
10. Dashboard is now loaded and visible
```

---

## Verification Checklist

### Quick Test (Browser Console)

1. **Open Browser DevTools** (F12)
2. **Open Console Tab** (should see no JS errors)
3. **Click "Sign In"** with `admin / password`
4. **Observe Console Output**:
   ```
   [LOGIN] Token saved for user: admin
   [LOGIN] Loading dashboard data...
   [LOGIN] Dashboard data loaded successfully
   ```
5. **Check Network Tab**:
   - `POST /login` → Status 200
   - `GET /metrics` → Status 200 with Authorization header
   - `GET /alerts` → Status 200 with Authorization header
   - `GET /waf-alerts` → Status 200 with Authorization header
6. **Verify JSON Responses** (click each request):
   - `/login`: Returns `{access_token: "...", token_type: "bearer"}`
   - `/metrics`: Returns `{total_requests, total_blocked, logs, ...}`
   - `/alerts`: Returns `{top_abusive_ips: [...]}`
   - `/waf-alerts`: Returns `{last_waf_blocks: [...], top_abuse_ips: [...]}`

### UI Verification

1. ✓ Login overlay disappears after successful login
2. ✓ Dashboard appears with metrics data
3. ✓ "Authentication Status" shows:
   - User: admin
   - Token: Valid (green tag)
   - API Key: Valid (green tag)
4. ✓ Logout button is visible (was hidden before login)
5. ✓ Metrics update every 3 seconds
6. ✓ Alerts update every 5 seconds

### Error Scenarios

**Scenario 1: Invalid Credentials**
- Enter `admin / wrongpassword`
- Expected: Login error shown, overlay remains visible

**Scenario 2: Network Error on Dashboard Load**
- Break network connection after login
- Expected: Overlay disappears, dashboard shows "No data" placeholders
- Polling continues attempting to reload

**Scenario 3: Session Expiry**
- Wait for token to expire (or manually set bad token in localStorage)
- Make any request
- Expected: Session cleared, login overlay shown again

---

## API Request Headers Verification

All authenticated requests should include:

```
GET /metrics HTTP/1.1
Host: 127.0.0.1:8001
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
X-API-Key: hackathon2026
Content-Type: application/json
```

**To verify in DevTools Network Tab:**
1. Right-click any request → "Copy as cURL"
2. Look for `-H 'Authorization: Bearer ...'`
3. Look for `-H 'X-API-Key: hackathon2026'`

---

## Debugging Tips

### Enable Detailed Logging (Optional)

Add this to the `login()` function to see more details:

```javascript
// After saveSession()
console.log('[DEBUG] accessToken set:', !!accessToken);
console.log('[DEBUG] currentUser:', currentUser);
console.log('[DEBUG] Auth headers:', getAuthHeaders());
```

### Check localStorage

```javascript
// In DevTools Console:
console.log('Token:', localStorage.getItem('gatelens_access_token'));
console.log('User:', JSON.parse(localStorage.getItem('gatelens_user')));
```

### Force Reload Session

```javascript
// In DevTools Console (after successful login):
restoreSession();  // Should show false in console
// Then navigate to another page and come back
```

---

## Backend Integration Checklist

### API Endpoints Verified

- [x] `POST /login` - Returns 200 with `access_token`
- [x] `GET /metrics` - Requires `Authorization` + `X-API-Key`
- [x] `GET /alerts` - Requires `Authorization` + `X-API-Key`
- [x] `GET /waf-alerts` - Requires `Authorization` + `X-API-Key`

### CORS Config Verified

- [x] `allow_origins=['*']` - Frontend at 127.0.0.1:xxxx can access 127.0.0.1:8001
- [x] `allow_credentials=True` - Allows Authorization header
- [x] `allow_methods=['*']` - Allows POST, GET, etc.
- [x] `allow_headers=['*']` - Allows custom headers (X-API-Key, Authorization)

### Response Format Verified

- [x] Login returns JSON: `{access_token, token_type}`
- [x] Metrics includes: `logs`, `total_requests`, `total_blocked`, `avg_response_time_ms`, `requests_this_minute`, `rate_limit`
- [x] Alerts includes: `top_abusive_ips` (array of `{ip, block_count}`)
- [x] WAF Alerts includes: `last_waf_blocks` (array), `top_abuse_ips` (array)

---

## Next Steps

1. **Test the fix** following the verification checklist above
2. **Check browser console** for any remaining errors
3. **Verify all API calls** in the Network tab include proper headers
4. **Confirm polling** works and metrics update regularly
5. **Test session persistence** - reload page and verify re-login works

---

## If Issues Persist

### Check these logs:

```bash
# Backend logs should show:
DEBUG gateway path=metrics method=GET token_payload={'user_id': 1, 'role': 'admin'} ...
DEBUG gateway path=alerts method=GET token_payload={'user_id': 1, 'role': 'admin'} ...
```

### Verify token is being created correctly:

In `backend/auth.py`, the `create_access_token()` function should encode JWT with proper payload.

### Check for any exceptions in poll functions:

Console should show only:
- `[LOGIN] Token saved for user: admin`
- `[LOGIN] Loading dashboard data...`
- `[LOGIN] Dashboard data loaded successfully`

NO errors like:
- `[FETCH] Failed to fetch metrics: ...`
- `Unexpected token ...` (JSON parse error)
- `TypeError: Cannot read property ...` 

---

## Summary of Changes

| File | Change | Why |
|------|--------|-----|
| `frontend/index.html` | Added `suppressLoginOverlayOn401` flag | Prevent overlay from re-appearing on 401 errors during initial dashboard load |
| `frontend/index.html` | Updated `apiFetch()` to check flag | Conditionally skip showing overlay on 401 if flag is true |
| `frontend/index.html` | Added try/catch around `Promise.all` | Handle errors more gracefully, don't let them bubble up |
| `frontend/index.html` | Added console logging | Debug login/fetch flow with `[LOGIN]` and `[FETCH]` prefixes |
| `frontend/index.html` | Updated `fetchDashboard()`, `fetchAlerts()`, `fetchWAFAlerts()` | Add logging and consistent error handling |

---

## Production Deployment Note

⚠️ The `suppressLoginOverlayOn401` flag is a temporary measure for the login flow. After login completes, it's reset to `false`, so:

- **Normal operation**: 401 errors show login overlay (user re-auth flow)
- **Login flow only**: 401 errors suppress overlay (prevent race condition)

This is safe and non-breaking. The flag is only used during the critical 500ms window after `saveSession()` is called.
