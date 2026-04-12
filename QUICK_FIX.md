# Quick Fix Commands

## The Issue
Frontend shows "Failed to fetch" - most likely because frontend is served via file:// instead of HTTP server.

## The Solution (3 Steps)

### Terminal 1: Start Backend
```bash
cd e:\api-gateway-hackathon\backend
python gateway.py
```
Wait for: `Uvicorn running on http://127.0.0.1:8000`

### Terminal 2: Start Frontend Server
```bash
cd e:\api-gateway-hackathon\frontend
python -m http.server 8001
```
Wait for: `Serving HTTP on 0.0.0.0 port 8001`

### Browser: Open Frontend
```
http://localhost:8001
```
(NOT file://, NOT 127.0.0.1)

---

## Verify It Works

### 1. Browser Console (F12)
```javascript
await diagnosticCheck()
```
Should show: `✅ BACKEND IS REACHABLE`

### 2. Login
- Username: `admin`
- Password: `password`
- Should hide overlay

### 3. Click Attack Button
- Click "SQL Injection" or any button
- Should see response in panel
- Should see detailed logs in console

---

## If Still Having Issues

### Check Protocol
```javascript
window.location.protocol  // Should be "http:" NOT "file:"
```

### Check API Configuration
```javascript
console.log(API_URL)  // Should be http://127.0.0.1:8000
```

### Check Backend Connectivity
```bash
curl http://127.0.0.1:8000/health
```
Should return: `{"status":"healthy","service":"backend"}`

---

## Process Management

### Kill Running Servers
```bash
# Windows - Close the terminal windows, or:
netstat -ano | findstr :8001  # Find PID
taskkill /PID <PID> /F        # Kill it

# Or just close Terminal 1 and Terminal 2
```

### Ports Used
- Backend: 8000
- Frontend Server: 8001
- Both must be free to start

