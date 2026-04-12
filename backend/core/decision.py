from typing import Any

from fastapi import Request

from core.config import ALERT_SCORE, BLOCK_SCORE, USER_TIERS
from core.state import (
    block_ip, is_ip_blocked,
    get_threat_score, increase_threat_score, decrease_threat_score, get_threat_level,
    THREAT_SCORE_THRESHOLD
)
from security.abuse import get_abuse_score, should_block_ip
from security.detector import detect_attacks
from security.rate_limit import get_rate_limit_for_request
from security.waf import WAFResult, run_waf_checks


def _normalize_reasons(reasons: list[str]) -> list[str]:
    """Deduplicate and normalize reasons list."""
    seen = {}
    result = []
    for reason in reasons:
        # Extract base reason (before = if present)
        base = reason.split('=')[0] if '=' in reason else reason
        if base not in seen:
            seen[base] = True
            result.append(reason)
    return result


async def evaluate_request(request: Request, body: bytes, ip: str) -> dict[str, Any]:
    score = 0
    reasons: list[str] = []

    detector_result = detect_attacks(request, body)
    score += detector_result["score"]
    reasons.extend(detector_result["reasons"])

    waf_result: WAFResult = await run_waf_checks(request, body)
    if is_ip_blocked(ip):
        score += BLOCK_SCORE
        reasons.append("ip_blacklist")

    score += waf_result.score
    if waf_result.reason and waf_result.reason != "OK":
        reasons.append(waf_result.reason)

    abuse_score = get_abuse_score(ip)
    if abuse_score:
        score += abuse_score * 5
        reasons.append(f"abuse={abuse_score}")

    rate_limit = get_rate_limit_for_request(request)
    rate_score = 2 if rate_limit == USER_TIERS.get("premium") else 5
    score += rate_score
    reasons.append(f"rate_limit={rate_limit}")

    reasons = _normalize_reasons(reasons)
    
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
    
    status = "allow"
    
    # CRITICAL: Ensure XSS and SQL injection are ALWAYS blocked
    # Check for attack detection patterns in reasons
    critical_attacks = ['xss', 'sqli', 'sql_injection', 'ml_xss', 'ml_sqli']
    has_critical_attack = any(attack in reason.lower() for reason in reasons for attack in critical_attacks)
    
    if has_critical_attack:
        status = "block"  # Always block XSS/SQLi, regardless of score
        block_ip(ip)
    elif waf_result.blocked:
        status = "block"
        block_ip(ip)
    elif should_block_ip(abuse_score):
        status = "block"
        block_ip(ip)
    elif current_threat_score >= THREAT_SCORE_THRESHOLD:  # NEW: Threat score threshold  
        status = "block"  # Block if threat score too high
        block_ip(ip)
    elif score >= BLOCK_SCORE:
        # Score-based block doesn't trigger IP block (legacy behavior)
        status = "block"
    elif score >= ALERT_SCORE:
        status = "alert"

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
