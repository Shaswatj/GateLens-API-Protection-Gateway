from typing import Any

from fastapi import Request

from core.config import ALERT_SCORE, BLOCK_SCORE, USER_TIERS
from core.state import block_ip, is_ip_blocked
from security.abuse import get_abuse_score, should_block_ip
from security.rate_limit import get_rate_limit_for_request
from security.waf import WAFResult, run_waf_checks


async def evaluate_request(request: Request, body: bytes, ip: str) -> dict[str, Any]:
    score = 0
    reasons: list[str] = []
    waf_result: WAFResult = await run_waf_checks(request, body)

    if is_ip_blocked(ip):
        score += BLOCK_SCORE
        reasons.append("ip_blacklist")

    score += waf_result.score
    if waf_result.reason:
        reasons.append(waf_result.reason)

    abuse_score = get_abuse_score(ip)
    if abuse_score:
        score += abuse_score * 5
        reasons.append(f"abuse={abuse_score}")

    rate_limit = get_rate_limit_for_request(request)
    rate_score = 2 if rate_limit == USER_TIERS.get("premium") else 5
    score += rate_score
    reasons.append(f"rate_limit={rate_limit}")

    if waf_result.blocked or should_block_ip(abuse_score) or score >= BLOCK_SCORE:
        decision = "block"
        block_ip(ip)
    elif score >= ALERT_SCORE:
        decision = "alert"
    else:
        decision = "allow"

    return {
        "decision": decision,
        "score": score,
        "reasons": reasons,
        "waf_result": waf_result,
        "rate_score": rate_score,
        "abuse_score": abuse_score,
    }
