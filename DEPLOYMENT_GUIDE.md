# DEPLOYMENT & OPERATION GUIDE

## Quick Start (After Fixes)

### Prerequisites
- Python 3.8+ installed
- Node.js/npm (if serving frontend separately)
- Backend dependencies: `pip install -r backend/requirements.txt`

### Step 1: Start Backend
```bash
cd backend
python gateway.py
```

**Expected Output:**
```
Uvicorn running on http://127.0.0.1:8001
```

### Step 2: Open Frontend
Option A - Direct file:
```bash
# Open in browser:
file:///path/to/api-gateway-hackathon/frontend/index.html
```

Option B - HTTP server:
```bash
# Terminal in root directory:
python -m http.server 8000

# Then open:
http://127.0.0.1:8000/frontend/index.html
```

### Step 3: Test Login
1. Enter credentials: `admin` / `password`
2. Click "Sign In"
3. **Expected**: Overlay disappears, dashboard loads with metrics

---

## What's Working Now

### ✓ Authentication Flow
- Login form submission → Backend validation
- JWT token generation (expires in 60 minutes)
- Token stored in localStorage
- Token included in all authenticated requests

### ✓ API Gateway Test Controls
- Normal Request (GET /users)
- SQL Injection test
- XSS test  
- Comment bypass test
- Encoded attack test
- Malformed payload test
- Unauthorized access test (RBAC)
- Path traversal test
- Query string injection test
- Rate limiting test (burst 35 requests)

### ✓ Dashboard Metrics
- Total Requests counter
- Total Blocked counter
- Average Response Time
- Requests per minute
- Real-time rate limiting indicator
- Traffic monitoring table (last 30 requests)
- Request logs (last 20)
- Security alerts
- WAF blocks tracking
- Abusive IP detection

### ✓ Session Management
- Auto-restore session on page reload (checks /metrics)
- Logout clears session and localStorage
- Automatic polling:
  - Metrics every 3 seconds
  - Alerts every 5 seconds
  - WAF alerts every 5 seconds

---

## Configuration

### Frontend Constants (index.html)
```javascript
const API_URL = 'http://127.0.0.1:8001';  // Backend URL
const API_KEY = 'hackathon2026';          // Shared API key
const STORAGE_TOKEN_KEY = 'gatelens_access_token';  // localStorage key
const STORAGE_USER_KEY = 'gatelens_user';
```

### Backend Configuration (core/config.py)
```python
SECRET_KEY = os.getenv("SECRET_KEY", "secret")        # JWT secret
API_KEY = os.getenv("API_KEY", "hackathon2026")       # API key
ALGORITHM = os.getenv("ALGORITHM", "HS256")           # JWT algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = 60                      # Token TTL
```

### Valid Credentials
- Admin: `admin` / `admin` or `admin` / `password`
- User: `user` / `user`

---

## Monitoring

### Console Output (Backend)
Watch for:
- `DEBUG gateway path=...` - Request processing
- `AUTH HEADER: Bearer ...` - Token validation
- `DECODED PAYLOAD: {user_id: ..., role: ...}` - JWT decode success
- `JWT ERROR: ...` - Token validation failure

### Console Output (Frontend)
After login, should see:
```
[LOGIN] Token saved for user: admin | Token length: 180
[LOGIN] Loading dashboard data...
[LOGIN] Dashboard data loaded successfully
```

Then every 3-5 seconds:
```
[FETCH] Metrics response not ok: 200  (if status isn't 200)
```

### Network Tab
After login, requests should have:
- **Authorization**: `Bearer eyJhbGciOiJIUzI1NiIs...` (JWT token)
- **X-API-Key**: `hackathon2026`
- **Content-Type**: `application/json`

Response codes:
- `/login`: 200 (success) or 401 (invalid credentials)
- `/metrics`, `/alerts`, `/waf-alerts`: 200 (success) or 401 (expired token)

---

## Common Issues & Solutions

### Issue: "Login overlay won't disappear"

**Solution**: Check browser console for errors
```javascript
// In DevTools Console:
localStorage.getItem('gatelens_access_token')  // Should have token
```

If null → Token not saved → Check backend /login response
If empty → Backend not returning access_token → Check backend code

### Issue: "401 Unauthorized on /metrics"

**Solution**: Verify JWT token
```javascript
// In DevTools Console:
const token = localStorage.getItem('gatelens_access_token');
const parts = token.split('.');
const payload = JSON.parse(atob(parts[1]));
console.log('Expires:', new Date(payload.exp * 1000));
console.log('Is valid:', payload.exp * 1000 > Date.now());
```

If expired → Login again
If invalid → Check backend SECRET_KEY matches

### Issue: "Polling not updating"

**Solution**: Check if requests are being sent
```javascript
// DevTools Network tab:
// Should see /metrics every 3 seconds
// Should see /alerts every 5 seconds
// All with 200 status
```

If no requests → Polling not started → Check if login succeeded
If 401 responses → Token invalid → Logout and login again

### Issue: "Session lost after page refresh"

**Solution**: Check localStorage and /metrics
```javascript
// Should see [RESTORE] logs in console
localStorage.getItem('gatelens_access_token')  // Should have token
```

If token present but still shows login → /metrics returning 401
→ Token invalid or backend issue

### Issue: "CORS error"

**Solution**: Verify frontend and backend URLs
```javascript
// Frontend check:
const API_URL = 'http://127.0.0.1:8001';  // Match actual backend URL

// Backend check:
allow_origins=['*']  // Should be in CORSMiddleware
```

If still failing:
- Check backend is actually running on port 8001
- Check frontend sent from different port/host
- Try: curl http://127.0.0.1:8001/metrics

---

## Troubleshooting Guide

### Step 1: Verify Backend Health
```bash
# Terminal:
curl -v http://127.0.0.1:8001/metrics \
  -H "X-API-Key: hackathon2026" \
  -H "Authorization: Bearer fake"

# Expected: 401 (invalid token accepted by header, rejected by JWT)
# Not: Connection refused, timeout, 404, 500
```

### Step 2: Test Full Login Flow
```bash
# Get token:
TOKEN=$(curl -s -X POST http://127.0.0.1:8001/login \
  -H "X-API-Key: hackathon2026" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"password"}' \
  | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)

echo "Token: $TOKEN"

# Use token:
curl -v http://127.0.0.1:8001/metrics \
  -H "X-API-Key: hackathon2026" \
  -H "Authorization: Bearer $TOKEN"

# Expected: 200 with metrics JSON
```

### Step 3: Check Frontend DevTools
```javascript
// Console:
console.log(localStorage.getItem('gatelens_access_token'))

// If null:
// 1. Check /login response has access_token
// 2. Check saveSession() is called
// 3. Check localStorage.setItem() works

// If token present:
// 1. Try manual /metrics call:
await fetch('http://127.0.0.1:8001/metrics', {
  headers: {
    'Authorization': 'Bearer ' + localStorage.getItem('gatelens_access_token'),
    'X-API-Key': 'hackathon2026'
  }
})
```

### Step 4: Check Browser Compatibility

**Tested on:**
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

**Required features:**
- localStorage
- Fetch API
- Promise/async-await
- ES6 features

---

## Performance Notes

### Request Latency
- Login request: ~10-50ms
- Polling requests: ~5-20ms per request
- Total overhead: ~60-100ms for 3 concurrent polls

### Polling Load
- 3 polling intervals: metrics (3s), alerts (5s), waf (5s)
- Estimated: 20-30 requests per minute
- Bandwidth: ~1-2 KB per request

### Recommended Limits
- Max polling intervals: Keep at 3s/5s (don't go lower)
- Max test buttons: ~10 concurrent (test rate limiting)
- Max session duration: Token expires in 60 minutes

---

## Security Notes

⚠️ **Production Deployment Considerations**

1. **JWT SECRET_KEY**
   - Default: `"secret"` ← NOT SECURE
   - Production: Generate strong random string (32+ chars)
   - Set via environment variable: `SECRET_KEY=your-secret-key`

2. **API_KEY**
   - Default: `"hackathon2026"`
   - Production: Use strong API key
   - Set via environment variable: `API_KEY=your-api-key`

3. **CORS Configuration**
   - Current: `allow_origins=['*']`
   - Production: Specify exact frontend URL
   ```python
   allow_origins=['https://example.com']
   ```

4. **HTTPS**
   - Frontend must use HTTPS in production
   - Backend should run behind HTTPS proxy

5. **Token Expiry**
   - Current: 60 minutes
   - Consider shorter TTL: 15-30 minutes
   - Implement refresh token flow

---

## Disaster Recovery

### If System Won't Start

1. **Backend won't start:**
   ```bash
   # Check Python installation:
   python --version
   
   # Check dependencies:
   pip install -r backend/requirements.txt
   
   # Try running with verbose output:
   python backend/gateway.py -v
   ```

2. **Frontend won't load:**
   - Check file path is correct
   - Check browser console for JavaScript errors
   - Check CORS errors in Network tab
   - Try opening DevTools (F12) to see errors

3. **Authentication broken:**
   - Check backend console for JWT ERROR
   - Verify SECRET_KEY in core/config.py
   - Verify .env file not overriding with wrong value
   - Restart backend

---

## Next Steps

### Post-Deployment Checklist
- [ ] Backend tested with curl commands
- [ ] Frontend loads without errors
- [ ] Login flow tested end-to-end
- [ ] Polling verified in Network tab
- [ ] All dashboard metrics display
- [ ] Page refresh maintains session
- [ ] Logout works and clears everything
- [ ] No console errors or warnings

### Future Improvements
- [ ] Implement refresh token flow
- [ ] Add activity logging
- [ ] Implement request signing
- [ ] Add rate limiting per user
- [ ] Implement 2FA
- [ ] Add audit trail
- [ ] Implement session revocation
- [ ] Add analytics dashboard

---

## Support

### Debugging Commands (DevTools Console)

```javascript
// Check login status
console.log('Logged in?', !!localStorage.getItem('gatelens_access_token'));

// Check token expiry
const token = localStorage.getItem('gatelens_access_token');
const exp = JSON.parse(atob(token.split('.')[1])).exp;
console.log('Expires in:', Math.round((exp * 1000 - Date.now()) / 1000), 'seconds');

// Force refresh polls
document.getElementById('rate-request')?.click();

// Clear session
localStorage.clear();
location.reload();

// Check all localStorage
for (let i = 0; i < localStorage.length; i++) {
  const key = localStorage.key(i);
  console.log(key, ':', localStorage.getItem(key));
}
```

### Useful curl Commands

```bash
# 1. Check backend is running
curl -v http://127.0.0.1:8001/metrics

# 2. Get auth token
curl -X POST http://127.0.0.1:8001/login \
  -H "X-API-Key: hackathon2026" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"password"}'

# 3. Call protected endpoint
curl -v http://127.0.0.1:8001/metrics \
  -H "X-API-Key: hackathon2026" \
  -H "Authorization: Bearer <token>"

# 4. Test with wrong credentials
curl -v http://127.0.0.1:8001/login \
  -H "X-API-Key: hackathon2026" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"wrong"}'
```

