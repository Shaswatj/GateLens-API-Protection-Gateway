# Network Diagnostics & "Failed to Fetch" Fix

## Problem
Frontend shows "Failed to fetch" when making API calls after login.

## Root Causes (in order of likelihood)

### 1. **Frontend served via file:// instead of http://** ⚠️ MOST COMMON
- **Symptom:** All API calls fail with "Failed to fetch"
- **Why:** Browsers block HTTP requests from file:// protocol (CORS security)
- **Solution:** Serve frontend via HTTP server, not file://

### 2. **Backend not running**
- **Symptom:** Health check fails
- **Why:** Backend must run before frontend
- **Solution:** Start backend first

### 3. **CORS misconfiguration**
- **Symptom:** Browser console shows CORS error
- **Why:** Backend not accepting requests from frontend origin
- **Solution:** Add CORS middleware (already done in gateway.py)

### 4. **Wrong API_URL**
- **Symptom:** URL shows wrong backend address
- **Solution:** Check API_URL constant

---

## DIAGNOSTIC CHECKLIST

### Step 1: Check Frontend Serving Protocol
**In Browser Console (F12):**
```javascript
// Paste this and press Enter
window.location.protocol
```
**Expected:** `http:` or `https:`  
**Problem:** `file:` ❌ This is the issue!

### Step 2: Check API Configuration
**In Browser Console:**
```javascript
console.log("API_URL:", API_URL);
console.log("API_KEY:", API_KEY);
```
**Expected:**
```
API_URL: http://127.0.0.1:8000
API_KEY: hackathon2026
```

### Step 3: Run Frontend Diagnostic
**In Browser Console:**
```javascript
await diagnosticCheck()
```
**Expected output:**
```
✅ BACKEND IS REACHABLE
```

**If it says "❌ BACKEND IS NOT REACHABLE":**
- Backend isn't running
- Wrong API_URL
- CORS blocking (check Network tab)

### Step 4: Check Network Tab
**In Browser DevTools:**
1. Open **Network** tab
2. Click an attack button (e.g., "SQL Injection")
3. Look for the request
4. Check the response status

**Common issues:**
- **CORS error in red** → Backend not accepting origin
- **"net::ERR_..." error** → Can't reach backend
- **Status 401** → Authentication issue
- **Status 403** → API key issue

### Step 5: Manual Backend Test
**In Python terminal (from project root):**
```bash
# Test with curl
curl -X GET http://127.0.0.1:8000/health \
  -H "X-API-Key: hackathon2026" \
  -H "Content-Type: application/json"

# Expected: {"status": "healthy", "service": "backend"}
```

---

## FIXES

### Fix 1: Serve Frontend via HTTP Server (MOST LIKELY SOLUTION)

**DO NOT:** Drag index.html into browser  
**DO:** Use a simple HTTP server

#### Option A: Python HTTP Server
```bash
# From project root
cd frontend
python -m http.server 8001
```
Then open: **http://localhost:8001**

#### Option B: Node HTTP Server
```bash
# Install globally (once)
npm install -g http-server

# Run from frontend directory
cd frontend
http-server -p 8001
```
Then open: **http://localhost:8001**

#### Option C: VS Code Live Server
1. Install "Live Server" extension in VS Code
2. Right-click index.html → "Open with Live Server"
3. Browser opens automatically with correct protocol

### Fix 2: Ensure Backend is Running
```bash
# From project root
cd backend
python gateway.py
```
**Expected output:**
```
INFO:     Uvicorn running on http://127.0.0.1:8000
```

### Fix 3: Verify CORS Configuration
**File:** `backend/gateway.py` (should have this at startup)
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)
```
✅ This is already configured in gateway.py

### Fix 4: Check API_URL in Frontend
**File:** `frontend/index.html` (line ~638)
```javascript
const API_URL = 'http://127.0.0.1:8000';
```
Must match backend's actual address.

---

## COMPLETE FIX PROCEDURE

### Step-by-Step Solution

1. **Open terminal in project root**
   ```bash
   cd e:\api-gateway-hackathon  # Your project path
   ```

2. **Start Backend (Terminal 1)**
   ```bash
   cd backend
   python gateway.py
   # Wait for: "Uvicorn running on http://127.0.0.1:8000"
   ```

3. **Start Frontend Server (Terminal 2)**
   ```bash
   cd frontend
   python -m http.server 8001
   # Will show: "Serving HTTP on 0.0.0.0 port 8001"
   ```

4. **Open in Browser**
   ```
   http://localhost:8001
   ```
   ✅ NOT file:// NOT 127.0.0.1:8001 - use localhost for CORS

5. **Verify Connection**
   Open Browser Console (F12) and run:
   ```javascript
   await diagnosticCheck()
   ```
   Should show: `✅ BACKEND IS REACHABLE`

6. **Test Login**
   - Username: `admin` (or `user`)
   - Password: `password` (or `user`)

7. **Test Attack Buttons**
   - Click "SQL Injection" or any attack button
   - Check response in panel below
   - Check console for detailed logs

---

## EXPECTED LOGS IN CONSOLE

### After clicking an attack button:

```
[ATTACK] ATTACK BUTTON CLICKED - sql-request
[REQUEST] Sending attack request
[REQUEST] Method: POST
[REQUEST] Path: /test-waf
[REQUEST] AccessToken exists: true
[REQUEST] Frontend origin: http://localhost:8001
[REQUEST] Backend URL: http://127.0.0.1:8000
[APIFETCH] URL: http://127.0.0.1:8000/test-waf
[APIFETCH] Method: POST
[RESPONSE] Status: 403
[RESPONSE] WAF Status: sql_injection_detected
[RESPONSE] WAF Reason: SQL injection pattern found
Completed /test-waf - Error 403
```

---

## TROUBLESHOOTING FLOWCHART

```
Frontend shows "Failed to fetch"
    ↓
Run: await diagnosticCheck()
    ↓
    ├─ ✅ BACKEND IS REACHABLE
    │  └─ ✅ Then check browser Network tab for CORS errors
    │
    └─ ❌ BACKEND IS NOT REACHABLE
       ├─ Is window.location.protocol === 'file:'?
       │  └─ YES → Use HTTP server (Fix 1)
       │
       ├─ Is backend running?
       │  └─ NO → Start backend (Fix 2)
       │
       ├─ Is API_URL correct?
       │  └─ NO → Update API_URL (Fix 4)
       │
       └─ else → Check firewall/ports
```

---

## QUICK VERIFICATION

1. **Backend Health Check:**
   ```bash
   curl http://127.0.0.1:8000/health
   ```

2. **Frontend Diagnostic:**
   ```javascript
   await diagnosticCheck()
   ```

3. **Login Test:**
   - User: admin / password
   - Should hide overlay and show dashboard

4. **Attack Button Test:**
   - Click any attack button
   - Should see response in test panel
   - Should see logs in console

---

## FILES MODIFIED FOR DIAGNOSTICS

1. **frontend/index.html**
   - Added `diagnosticCheck()` function
   - Enhanced error logging in `apiFetch()`
   - Enhanced error logging in `performTestRequest()`
   - Diagnostic output includes frontend protocol, backend URL, and detailed error messages

2. **backend/gateway.py** (no changes needed)
   - Already has CORS configured

---

## SUMMARY

| Issue | Cause | Fix |
|-------|-------|-----|
| "Failed to fetch" | file:// protocol | Use HTTP server |
| Network error | Backend not running | Start backend first |
| CORS error | Missing CORS headers | Already configured |
| 401 error | No token/expired token | Login again |
| 403 error | Missing API key | Check headers |
| Wrong endpoint | Bad API_URL | Verify API_URL |

