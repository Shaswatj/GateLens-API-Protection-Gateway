# Smart Threat Scoring - Code Reference

This document contains the exact code changes made to implement the smart threat scoring system.

## File 1: backend/core/state.py

### New Module-Level Variables (lines 9-12)
```python
# Threat scoring system (NEW - non-breaking addition)
ip_scores: dict[str, int] = {}  # Maps IP to threat score
ip_last_seen: dict[str, float] = {}  # Maps IP to last activity timestamp
THREAT_SCORE_THRESHOLD = 10  # Block if score >= this value
SCORE_DECAY_TIMEOUT = 10  # Seconds of inactivity before score decay
```

### New Functions (lines 68-159)

```python
def get_threat_score(ip: str) -> int:
    """Get current threat score for an IP. Includes time-based decay."""
    if ip not in ip_scores:
        return 0
    
    # Apply time-based decay: reduce score if no recent activity
    current_time = time.time()
    if ip in ip_last_seen:
        time_since_last_seen = current_time - ip_last_seen[ip]
        if time_since_last_seen > SCORE_DECAY_TIMEOUT:
            # Decay score: reduce by 1 per SCORE_DECAY_TIMEOUT period
            decay_periods = int(time_since_last_seen / SCORE_DECAY_TIMEOUT)
            ip_scores[ip] = max(0, ip_scores[ip] - decay_periods)
            ip_last_seen[ip] = current_time
    
    return ip_scores[ip]


def increase_threat_score(ip: str, amount: int) -> int:
    """Increase threat score for an IP based on attack severity.
    
    Returns the new score.
    """
    current_time = time.time()
    ip_scores[ip] = ip_scores.get(ip, 0) + amount
    ip_last_seen[ip] = current_time
    return ip_scores[ip]


def decrease_threat_score(ip: str, amount: int = 1) -> int:
    """Decrease threat score on normal request (recovery).
    
    Returns the new score (minimum 0).
    """
    current_time = time.time()
    ip_scores[ip] = max(0, ip_scores.get(ip, 0) - amount)
    ip_last_seen[ip] = current_time
    return ip_scores[ip]


def get_threat_level(score: int) -> str:
    """Return threat level based on score: low, medium, high"""
    if score >= THREAT_SCORE_THRESHOLD:
        return "high"
    elif score >= (THREAT_SCORE_THRESHOLD * 0.6):  # 60% of threshold
        return "medium"
    else:
        return "low"


def clear_threat_score(ip: str) -> bool:
    """Clear threat score for an IP. Returns True if score existed."""
    if ip in ip_scores:
        del ip_scores[ip]
        if ip in ip_last_seen:
            del ip_last_seen[ip]
        return True
    return False


def clear_all_threat_scores() -> int:
    """Clear all threat scores. Returns count of cleared IPs."""
    count = len(ip_scores)
    ip_scores.clear()
    ip_last_seen.clear()
    return count
```

---

## File 2: backend/core/decision.py

### Import Fix (lines 4-8)
**BEFORE:**
```python
from core.state import (
    block_ip, is_ip_blocked,
    get_threat_score, increase_threat_score, decrease_threat_score, get_threat_level
)
```

**AFTER:**
```python
from core.state import (
    block_ip, is_ip_blocked,
    get_threat_score, increase_threat_score, decrease_threat_score, get_threat_level,
    THREAT_SCORE_THRESHOLD  # ADDED
)
```

### New Threat Scoring Integration (lines 60-95)

Insert this after the WAF/detector evaluation and before the decision logic:

```python
    # ============================================
    # THREAT SCORING INTEGRATION (NEW)
    # ============================================
    
    # Get current threat score with time-based decay applied
    current_threat_score = get_threat_score(ip)
    threat_level = get_threat_level(current_threat_score)
    
    # Detect if this is an attack and increase score accordingly
    has_attack = len([r for r in reasons if any(
        att in r.lower() for att in ['xss', 'sqli', 'sql_injection', 'ml_xss', 'ml_sqli', 'path_traversal', 'abuse']
    )]) > 0
    
    if has_attack:
        # Increase threat score based on attack type
        attack_increment = 0
        if any(att in r.lower() for r in reasons for att in ['sqli', 'sql_injection', 'ml_sqli']):
            attack_increment += 5  # SQLi: +5
        if any(att in r.lower() for r in reasons for att in ['xss', 'ml_xss']):
            attack_increment += 4  # XSS: +4
        if any('path_traversal' in r.lower() for r in reasons):
            attack_increment += 3  # Path traversal: +3
        if any('abuse' in r.lower() for r in reasons):
            attack_increment += 2  # Abuse pattern: +2
        
        if attack_increment > 0:
            current_threat_score = increase_threat_score(ip, attack_increment)
            threat_level = get_threat_level(current_threat_score)
    else:
        # Normal request: reduce threat score (recovery)
        current_threat_score = decrease_threat_score(ip, 1)
        threat_level = get_threat_level(current_threat_score)
    
    # ============================================
    # DECISION LOGIC WITH THREAT SCORING
    # ============================================
```

### Decision Logic Modification (around line 115-120)

Add this condition in the decision tree:

```python
    elif current_threat_score >= THREAT_SCORE_THRESHOLD:  # NEW: Threat score threshold  
        status = "block"  # Block if threat score too high
        block_ip(ip)
```

### Response Enhancement (lines 138-142)

Add these fields to the return dictionary:

```python
    return {
        "status": status,
        "score": score,
        "reason": reasons[0] if reasons else "ok",
        "reasons": reasons,
        "decision": status,
        "ip_score": current_threat_score,  # NEW: Threat score
        "threat_level": threat_level,  # NEW: Low/Medium/High
        "waf_result": {
            "blocked": waf_result.blocked,
            "alert": waf_result.alert,
            "score": waf_result.score,
            "reason": waf_result.reason,
            "block_type": waf_result.block_type,
        },
        "rate_score": rate_score,
        "abuse_score": abuse_score,
    }
```

---

## File 3: backend/gateway.py

### Response Enhancements 

Look for the response formatting in the gateway endpoints. Add the threat scoring fields:

#### In 403 Block Response (around line 321-327):
```python
return {
    'detail': {
        'message': 'Request blocked for security reasons',
        'ip_score': result.get('ip_score', 0),        # NEW
        'threat_level': result.get('threat_level', 'unknown'),  # NEW
        'reason': result.get('reason', 'unknown'),
        'timestamp': timestamp,
    }
}
```

#### In 200 Success Response (around line 338-344):
```python
return {
    'message': 'Request processed',
    'ip_score': result.get('ip_score', 0),        # NEW
    'threat_level': result.get('threat_level', 'unknown'),  # NEW
    'data': {...},
    'timestamp': timestamp,
}
```

---

## Configuration

### Adjustable Parameters

All in `backend/core/state.py`:

```python
THREAT_SCORE_THRESHOLD = 10         # Minimum score to trigger blocking
SCORE_DECAY_TIMEOUT = 10            # Seconds between decay periods

# Attack severity values (in decision.py):
SQLi = 5                            # SQL Injection
XSS = 4                             # Cross-Site Scripting  
Path_Traversal = 3                  # Path Traversal
Abuse = 2                           # Abuse Pattern
Normal_Recovery = -1                # Normal Request (recovery)
```

### Block Timeout

Already configured in `core/config.py`:
```python
DEMO_MODE = true                    # 10-second blocks
DEMO_MODE = false                   # 300-second blocks
```

---

## Testing Changes

### Verification Script

The system includes `final_verification.py` that tests:
1. Baseline normal request (score=0)
2. SQLi attack detection (+5)
3. XSS attack detection (+4)
4. Threshold reaching (+5+4=9, then +4=13 > 10)
5. Continued blocking at high threat
6. Recovery through normal requests (-1 each)

Run with:
```bash
cd backend
python final_verification.py
```

---

## Summary of Changes

| Component | Type | Lines | Breaking? |
|-----------|------|-------|-----------|
| state.py | New functions | +92 | No |
| decision.py | Integration | +35 | No |
| decision.py | Import fix | +1 | No |
| gateway.py | Response fields | +4 | No |
| **Total** | | **+132** | **No** |

All changes are additions or extensions. No existing code was modified or removed.

