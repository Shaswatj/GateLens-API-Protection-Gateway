param()

$API_URL = "http://127.0.0.1:8000"
$API_KEY = "hackathon2026"

Write-Host ""
Write-Host "======== LAYER ISOLATION DEBUG ========" -ForegroundColor Cyan
Write-Host ""

# PHASE 1: Backend check
Write-Host "[PHASE 1] Backend Response Check" -ForegroundColor Yellow
try {
    $r = Invoke-WebRequest "$API_URL/metrics" -UseBasicParsing -ErrorAction Stop -TimeoutSec 2
    Write-Host "✓ Backend running" -ForegroundColor Green
} catch {
    Write-Host "✗ Backend not responding" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "[PHASE 2] Auth Layer Test" -ForegroundColor Yellow

# Test missing API key
Write-Host "  [2.1] No API key (expect 401)" -ForegroundColor Cyan
try {
    Invoke-WebRequest "$API_URL/metrics" -UseBasicParsing -ErrorAction Stop | Out-Null
    Write-Host "  ✗ Got 200 - AUTH NOT ENFORCED" -ForegroundColor Red
} catch {
    $code = $_.Exception.Response.StatusCode.Value__
    if ($code -eq 401) {
        Write-Host "  ✓ Auth working (401)" -ForegroundColor Green
    } else {
        Write-Host "  ✗ Wrong code: $code" -ForegroundColor Red
    }
}

# Test invalid API key
Write-Host "  [2.2] Invalid API key (expect 401)" -ForegroundColor Cyan
try {
    Invoke-WebRequest "$API_URL/metrics" -Headers @{"X-API-Key"="INVALID"} -UseBasicParsing -ErrorAction Stop | Out-Null
    Write-Host "  ✗ Got 200 - Auth bypassed" -ForegroundColor Red
} catch {
    $code = $_.Exception.Response.StatusCode.Value__
    if ($code -eq 401) {
        Write-Host "  ✓ Auth working (401)" -ForegroundColor Green
    } else {
        Write-Host "  ✗ Wrong code: $code" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "[PHASE 3] Generate JWT Token" -ForegroundColor Yellow
$loginBody = @{username="Errorcode"; password="intrusionx"} | ConvertTo-Json
$headers = @{"X-API-Key"=$API_KEY}

try {
    $r = Invoke-WebRequest "$API_URL/login" -Method POST -Body $loginBody -ContentType "application/json" -Headers $headers -UseBasicParsing -ErrorAction Stop
    $data = $r.Content | ConvertFrom-Json
    $JWT = $data.access_token
    Write-Host "✓ JWT Generated" -ForegroundColor Green
    Write-Host "  Token: $($JWT.Substring(0,40))..." -ForegroundColor Gray
} catch {
    Write-Host "✗ Login failed" -ForegroundColor Red
    exit 1
}

$validHeaders = @{
    "X-API-Key" = $API_KEY
    "Authorization" = "Bearer $JWT"
}

Write-Host ""
Write-Host "[PHASE 4] Clear Blocked IPs" -ForegroundColor Yellow
try {
    $r = Invoke-WebRequest "$API_URL/clear-ip" -Method POST -Headers $validHeaders -UseBasicParsing -ErrorAction Stop
    $data = $r.Content | ConvertFrom-Json
    Write-Host "✓ Cleared $($data.cleared_count) blocked IPs" -ForegroundColor Green
} catch {
    Write-Host "⚠ Could not clear IPs" -ForegroundColor Yellow
}

Start-Sleep -Seconds 2

Write-Host ""
Write-Host "[PHASE 5] Normal Request (Full Stack)" -ForegroundColor Yellow
try {
    $r = Invoke-WebRequest "$API_URL/test?param=hello" -Headers $validHeaders -UseBasicParsing -ErrorAction Stop
    $data = $r.Content | ConvertFrom-Json
    Write-Host "✓ REQUEST ALLOWED (200)" -ForegroundColor Green
    Write-Host "  Status: $($data.status)" -ForegroundColor Gray
    Write-Host "  Score: $($data.score)" -ForegroundColor Gray
} catch {
    $code = $_.Exception.Response.StatusCode.Value__
    Write-Host "✗ REQUEST BLOCKED ($code)" -ForegroundColor Red
    
    if ($code -eq 401) {
        Write-Host "  ROOT CAUSE: AUTH layer (credentials issue)" -ForegroundColor Yellow
    } elseif ($code -eq 429) {
        Write-Host "  ROOT CAUSE: RATE LIMIT exceeded" -ForegroundColor Yellow
    } elseif ($code -eq 403) {
        Write-Host "  ROOT CAUSE: WAF layer (IP blocked or attack detected)" -ForegroundColor Yellow
    }
}

Start-Sleep -Seconds 2

Write-Host ""
Write-Host "[PHASE 6] XSS Detection Test" -ForegroundColor Yellow
try {
    $r = Invoke-WebRequest "$API_URL/test?param=<script>alert(1)</script>" -Headers $validHeaders -UseBasicParsing -ErrorAction Stop
    Write-Host "  ✗ XSS NOT BLOCKED (200 unexpected)" -ForegroundColor Red
} catch {
    $code = $_.Exception.Response.StatusCode.Value__
    if ($code -eq 403) {
        Write-Host "  ✓ XSS correctly blocked (403)" -ForegroundColor Green
    } else {
        Write-Host "  ? Unexpected code: $code" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "======== DEBUG COMPLETE ========" -ForegroundColor Cyan
