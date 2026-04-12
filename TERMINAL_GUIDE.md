# Step-by-Step Terminal Guide

## The Problem
You're getting "Failed to fetch" errors when the frontend tries to call backend APIs after login.

## The Cause
Your frontend is being opened from file:// instead of being served via HTTP. Browsers block HTTP requests from file:// URLs for security reasons.

## The Solution
Serve the frontend using an HTTP server. Do this in 3 simple steps.

---

## STEP 1: Start Backend
**Open Terminal in project root:**

```bash
# Navigate to backend folder
cd backend

# Start the backend server
python gateway.py
```

**You should see:**
```
INFO:     Started server process [12345]
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

✅ **KEEP THIS RUNNING** - Don't close terminal

---

## STEP 2: Start Frontend Server
**Open NEW Terminal in project root:**

```bash
# Navigate to frontend folder
cd frontend

# Start simple HTTP server
python -m http.server 8001
```

**You should see:**
```
Serving HTTP on 0.0.0.0 port 8001 (http://0.0.0.0:8001/)
```

✅ **KEEP THIS RUNNING** - Don't close terminal

---

## STEP 3: Open in Browser
**Open your browser and go to:**
```
http://localhost:8001
```

✅ **NOT** `file:///...` path  
✅ **NOT** `127.0.0.1:8001` (use localhost for CORS)

---

## STEP 4: Verify It Works

### Check Backend Is Reachable
Open **Browser Console** (Press F12, click "Console" tab)

Paste this code:
```javascript
await diagnosticCheck()
```

Press Enter.

**Expected output:**
```
=============== FRONTEND DIAGNOSTIC CHECK ===============
1. Frontend Protocol: http:
2. Frontend Origin: http://localhost:8001
3. Backend URL: http://127.0.0.1:8000
4. Testing backend connectivity...
5. Backend health check: 200 true
   Response: {status: 'healthy', service: 'backend'}
✅ BACKEND IS REACHABLE
```

✅ If you see this: **Connection is working!**

❌ If you see "BACKEND IS NOT REACHABLE": See troubleshooting below.

---

## STEP 5: Test Login

1. Enter credentials:
   - Username: `admin`
   - Password: `password`

2. Click "Sign In"

3. The login overlay should disappear and show dashboard

**Check console for:**
```
[LOGIN] Login successful
[LOGIN] Hiding overlay
```

---

## STEP 6: Test Attack Buttons

1. Click any attack button (e.g., "SQL Injection")

2. You should see response in the "Test Response" panel

3. Check console for detailed logs like:
```
[ATTACK] ATTACK BUTTON CLICKED - sql-request
[REQUEST] Sending attack request
[REQUEST] AccessToken exists: true
[RESPONSE] Status: 403
[RESPONSE] WAF Status: sql_injection_detected
Completed /test-waf - Error 403
```

---

## EXPECTED RESULTS

### Success Indicators

1. ✅ No "Failed to fetch" errors
2. ✅ `await diagnosticCheck()` shows "BACKEND IS REACHABLE"
3. ✅ Login works without network errors
4. ✅ Attack buttons return responses
5. ✅ Console shows detailed logs
6. ✅ Browser DevTools Network tab shows HTTP requests with status codes

---

## TROUBLESHOOTING

### Issue 1: "BACKEND IS NOT REACHABLE"

**Check these things:**

1. **Is Terminal 1 running?**
   ```bash
   # Terminal 1 should have:
   INFO:     Uvicorn running on http://127.0.0.1:8000
   ```

2. **Test backend directly:**
   ```bash
   curl http://127.0.0.1:8000/health
   ```
   Should return: `{"status":"healthy","service":"backend"}`

3. **Check your project path:**
   Make sure you're in the right directory

4. **Check Python version:**
   ```bash
   python --version
   ```
   Should be Python 3.7+

### Issue 2: "Port Already in Use"

```bash
# For port 8000
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# For port 8001
netstat -ano | findstr :8001
taskkill /PID <PID> /F
```

Or just close the terminal and try different ports:
```bash
# Try port 8002 instead
python -m http.server 8002
# Then open: http://localhost:8002
```

### Issue 3: "Modules Not Found"

```bash
# Install dependencies
pip install fastapi uvicorn

# Or from project root
pip install -r backend/requirements.txt
```

### Issue 4: "It's Still Not Working"

1. **Check frontend protocol:**
   ```javascript
   window.location.protocol
   ```
   Must show `http:` not `file:`

2. **Check API_URL:**
   ```javascript
   console.log(API_URL)
   ```
   Must show `http://127.0.0.1:8000`

3. **Check Browser Console for errors:**
   - Press F12
   - Look for red error messages
   - Look for CORS errors

4. **Try another HTTP server:**
   ```bash
   # Option A: Node
   npm install -g http-server
   cd frontend
   http-server -p 8001

   # Option B: VS Code Live Server
   # Install extension in VS Code
   # Right-click index.html → "Open with Live Server"
   ```

---

## TERMINAL LAYOUT

You should have 2 terminals open:

**Terminal 1 (Backend):**
```
$ cd backend
$ python gateway.py
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete
← KEEP RUNNING
```

**Terminal 2 (Frontend):**
```
$ cd frontend
$ python -m http.server 8001
Serving HTTP on 0.0.0.0 port 8001
← KEEP RUNNING
```

**Browser:**
```
http://localhost:8001
```

---

## QUICK VALIDATION CHECKLIST

Run these in Browser Console (F12) to verify:

```javascript
// 1. Check frontend protocol
window.location.protocol === 'http:' ? '✅ HTTP' : '❌ FILE'

// 2. Check backend URL
API_URL === 'http://127.0.0.1:8000' ? '✅ Correct' : '❌ Wrong'

// 3. Run test
await diagnosticCheck()

// 4. Check token
console.log('Token exists:', !!accessToken)
```

---

## SHUTDOWN

When done testing:

1. **Terminal 1 (Backend):** Press `Ctrl+C`
2. **Terminal 2 (Frontend):** Press `Ctrl+C`
3. **Browser:** Close or navigate away

Can restart anytime by repeating STEP 1-3.

---

## ONE-LINER QUICK START

### Windows PowerShell
```powershell
# Terminal 1
cd backend; python gateway.py

# Terminal 2  
cd frontend; python -m http.server 8001
```

### Linux/Mac
```bash
# Terminal 1
cd backend && python gateway.py

# Terminal 2
cd frontend && python -m http.server 8001
```

Then open: `http://localhost:8001`

---

## Files for Reference

- **QUICK_FIX.md** - Quick summary
- **NETWORK_DIAGNOSTICS.md** - Detailed diagnostics
- **SOLUTION_SUMMARY.md** - Full technical summary

