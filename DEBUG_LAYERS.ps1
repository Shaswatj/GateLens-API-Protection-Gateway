# ============================================
# LAYER-BY-LAYER DEBUGGING SCRIPT
# Isolates Auth, WAF, and UI issues
# ============================================

$API_URL = "http://127.0.0.1:8000"
$API_KEY = "hackathon2026"
$TEST_IP = "127.0.0.1"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "LAYER ISOLATION DEBUGGING" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# ============================================
# PHASE 1: SYSTEM STATE CHECK
# ============================================

Write-Host "" 
Write-Host "[PHASE 1] SYSTEM STATE CHECK" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Yellow

# Test 1.1: Backend is running?
Write-Host ""
Write-Host "[1.1] Is backend running?" -ForegroundColor Cyan
try {
    $response = Invoke-WebRequest -Uri "$API_URL/metrics" -UseBasicParsing -ErrorAction Stop -TimeoutSec 2
    Write-Host "✓ Backend RESPONSIVE (Status: $($response.StatusCode))" -ForegroundColor Green
} catch {
    Write-Host "✗ Backend NOT RESPONDING" -ForegroundColor Red
    Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# ============================================
# PHASE 2: AUTH LAYER - ISOLATION TEST
# ============================================

Write-Host "`n[PHASE 2] AUTH LAYER TESTS" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Yellow

# Test 2.1: Missing API key
Write-Host "`n[2.1] Missing API Key (should be 401)" -ForegroundColor Cyan
try {
    $response = Invoke-WebRequest -Uri "$API_URL/metrics" -UseBasicParsing -ErrorAction Stop
    Write-Host "✗ UNEXPECTED 200 - API key check may be broken" -ForegroundColor Red
} catch {
    $statusCode = $_.Exception.Response.StatusCode.Value__
    $detail = $_.Exception.Response.StatusDescription
    if ($statusCode -eq 401) {
        Write-Host "✓ Correctly returned 401 (missing API key)" -ForegroundColor Green
    } else {
        Write-Host "✗ Unexpected $statusCode ($detail)" -ForegroundColor Red
    }
}

# Test 2.2: Invalid API key
Write-Host "`n[2.2] Invalid API Key (should be 401)" -ForegroundColor Cyan
$headers = @{ "X-API-Key" = "INVALID_KEY_12345" }
try {
    $response = Invoke-WebRequest -Uri "$API_URL/metrics" -Headers $headers -UseBasicParsing -ErrorAction Stop
    Write-Host "✗ UNEXPECTED 200 - Invalid key was accepted!" -ForegroundColor Red
} catch {
    $statusCode = $_.Exception.Response.StatusCode.Value__
    if ($statusCode -eq 401) {
        Write-Host "✓ Correctly returned 401 (invalid API key)" -ForegroundColor Green
    } else {
        Write-Host "✗ Unexpected $statusCode" -ForegroundColor Red
    }
}

# Test 2.3: Valid API key but no JWT
Write-Host "`n[2.3] Valid API Key but Missing JWT (should be 401)" -ForegroundColor Cyan
$headers = @{ "X-API-Key" = $API_KEY }
try {
    $response = Invoke-WebRequest -Uri "$API_URL/metrics" -Headers $headers -UseBasicParsing -ErrorAction Stop
    Write-Host "✗ UNEXPECTED 200 - JWT check may be broken" -ForegroundColor Red
} catch {
    $statusCode = $_.Exception.Response.StatusCode.Value__
    if ($statusCode -eq 401) {
        Write-Host "✓ Correctly returned 401 (missing JWT)" -ForegroundColor Green
    } else {
        Write-Host "✗ Unexpected $statusCode" -ForegroundColor Red
    }
}

# ============================================
# PHASE 3: GENERATE VALID JWT TOKEN
# ============================================

Write-Host "`n[PHASE 3] GENERATE VALID JWT TOKEN" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Yellow

Write-Host "`n[3.1] Login (get valid JWT)" -ForegroundColor Cyan
$loginPayload = @{
    username = "Errorcode"
    password = "intrusionx"
} | ConvertTo-Json

$headers = @{ "X-API-Key" = $API_KEY }
try {
    $response = Invoke-WebRequest -Uri "$API_URL/login" -Method POST -Body $loginPayload `
        -ContentType "application/json" -Headers $headers -UseBasicParsing -ErrorAction Stop
    $loginData = $response.Content | ConvertFrom-Json
    $JWT_TOKEN = $loginData.access_token
    Write-Host "✓ Got valid JWT token" -ForegroundColor Green
    Write-Host "  Token (first 50 chars): $($JWT_TOKEN.Substring(0, [Math]::Min(50, $JWT_TOKEN.Length)))..." -ForegroundColor Gray
} catch {
    Write-Host "✗ FAILED to get JWT token" -ForegroundColor Red
    Write-Host "  Error: $($_.Exception.Response.StatusCode.Value__)" -ForegroundColor Red
    exit 1
}

# ============================================
# PHASE 4: CREATE HEADERS FOR NORMAL REQUESTS
# ============================================

Write-Host "`n[PHASE 4] PREPARE HEADERS" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Yellow

$validHeaders = @{
    "X-API-Key"     = $API_KEY
    "Authorization" = "Bearer $JWT_TOKEN"
}

Write-Host "`n✓ Headers prepared:" -ForegroundColor Cyan
Write-Host "  X-API-Key: $API_KEY" -ForegroundColor Gray
Write-Host "  Authorization: Bearer [token]" -ForegroundColor Gray

# ============================================
# PHASE 5: WAF LAYER - IP BLOCKING STATE
# ============================================

Write-Host "`n[PHASE 5] WAF LAYER - IP BLOCKING STATE" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Yellow

Write-Host "`n[5.1] Clear any blocked IPs first" -ForegroundColor Cyan
try {
    $response = Invoke-WebRequest -Uri "$API_URL/clear-ip" -Method POST -Headers $validHeaders `
        -UseBasicParsing -ErrorAction Stop
    $clearData = $response.Content | ConvertFrom-Json
    Write-Host "✓ Cleared blocked IPs: $($clearData.cleared_count) IPs removed" -ForegroundColor Green
} catch {
    $statusCode = $_.Exception.Response.StatusCode.Value__
    Write-Host "⚠ Clear IP status: $statusCode" -ForegroundColor Yellow
}

# Wait for cooldown
Write-Host "`n[5.2] Waiting for request cooldown (2 seconds)..." -ForegroundColor Gray
Start-Sleep -Seconds 2

# ============================================
# PHASE 6: NORMAL REQUEST - FULL AUTH + WAF
# ============================================

Write-Host "`n[PHASE 6] TEST NORMAL REQUEST (Full Stack)" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Yellow

Write-Host "`n[6.1] Normal benign request" -ForegroundColor Cyan
try {
    $response = Invoke-WebRequest -Uri "$API_URL/test?param=hello" -Headers $validHeaders `
        -UseBasicParsing -ErrorAction Stop
    $data = $response.Content | ConvertFrom-Json
    Write-Host "✓ REQUEST SUCCEEDED (Status 200)" -ForegroundColor Green
    Write-Host "  Status: $($data.status)" -ForegroundColor Gray
    Write-Host "  Score: $($data.score)" -ForegroundColor Gray
    Write-Host "  Reasons: $($data.reasons)" -ForegroundColor Gray
} catch {
    $statusCode = $_.Exception.Response.StatusCode.Value__
    Write-Host "✗ REQUEST FAILED (Status $statusCode)" -ForegroundColor Red
    
    # Try to extract error details
    try {
        $errorData = $_.Exception.Response.GetResponseStream() | ConvertFrom-Json
        Write-Host "  Error detail: $($errorData.detail)" -ForegroundColor Red
    } catch {
        Write-Host "  Could not parse error response" -ForegroundColor Red
    }
    
    # Diagnostic questions
    Write-Host "`n[DIAGNOSTIC] Which layer failed?" -ForegroundColor Yellow
    if ($statusCode -eq 401) {
        Write-Host "  → AUTH LAYER (missing/invalid credentials)" -ForegroundColor Red
    } elseif ($statusCode -eq 429) {
        Write-Host "  → WAF LAYER (rate limited)" -ForegroundColor Red
    } elseif ($statusCode -eq 403) {
        Write-Host "  → WAF LAYER (blocked - IP or attack detection)" -ForegroundColor Red
    } else {
        Write-Host "  → UNKNOWN ($statusCode)" -ForegroundColor Red
    }
}

# ============================================
# PHASE 7: RATE LIMIT STATE CHECK
# ============================================

Write-Host "`n[PHASE 7] RATE LIMIT STATE" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Yellow

Write-Host "`n[7.1] Check metrics (shows total requests)" -ForegroundColor Cyan
try {
    $response = Invoke-WebRequest -Uri "$API_URL/metrics" -Headers $validHeaders `
        -UseBasicParsing -ErrorAction Stop
    $metricsData = $response.Content | ConvertFrom-Json
    Write-Host "✓ Got metrics" -ForegroundColor Green
    Write-Host "  Total requests: $($metricsData.total_requests)" -ForegroundColor Gray
    if ($metricsData.PSObject.Properties.Name -contains 'rate_limited_count') {
        Write-Host "  Rate limited: $($metricsData.rate_limited_count)" -ForegroundColor Gray
    }
} catch {
    Write-Host "✗ Could not fetch metrics" -ForegroundColor Red
}

# ============================================
# PHASE 8: ATTACK DETECTION (WAF PATTERNS)
# ============================================

Write-Host "`n[PHASE 8] WAF PATTERN DETECTION" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Yellow

Write-Host "`n[8.1] Test XSS detection (should block with 403)" -ForegroundColor Cyan
Start-Sleep -Seconds 2
try {
    $xssPayload = '<script>alert("xss")</script>'
    $response = Invoke-WebRequest -Uri "$API_URL/test?param=$xssPayload" -Headers $validHeaders `
        -UseBasicParsing -ErrorAction Stop
    Write-Host "✗ XSS NOT BLOCKED (unexpected success)" -ForegroundColor Red
} catch {
    $statusCode = $_.Exception.Response.StatusCode.Value__
    if ($statusCode -eq 403) {
        Write-Host "✓ XSS correctly blocked (403)" -ForegroundColor Green
    } else {
        Write-Host "✗ Unexpected status: $statusCode" -ForegroundColor Red
    }
}

# ============================================
# SUMMARY
# ============================================

Write-Host "`n[SUMMARY] KEY FINDINGS" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan

Write-Host "`nTo find root cause, look for:" -ForegroundColor Yellow
Write-Host "  1. If Phase 2 fails: AUTH LAYER BROKEN" -ForegroundColor Gray
Write-Host "  2. If Phase 6 returns 401: Missing/expired JWT" -ForegroundColor Gray
Write-Host "  3. If Phase 6 returns 429: RATE LIMIT EXCEEDED" -ForegroundColor Gray
Write-Host "  4. If Phase 6 returns 403: IP BLOCKED or ATTACK DETECTED" -ForegroundColor Gray
Write-Host "  5. If Phase 8 returns 200: WAF PATTERNS NOT WORKING" -ForegroundColor Gray

Write-Host "`nNext step:" -ForegroundColor Yellow
Write-Host "  Run this script and paste the failures here for analysis" -ForegroundColor Gray
