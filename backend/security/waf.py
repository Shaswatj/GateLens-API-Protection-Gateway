import json
import re
from dataclasses import dataclass
from urllib.parse import unquote_plus
from fastapi import Request

from core.config import ALERT_SCORE, BLOCK_SCORE, MALICIOUS_BODY_PATTERNS, MALICIOUS_HEADER_PATTERNS


@dataclass
class WAFResult:
    blocked: bool = False
    alert: bool = False
    score: int = 0
    reason: str = ""
    block_type: str = ""


def header_check(request: Request) -> bool:
    headers_text = str(dict(request.headers)).lower()
    for pattern in MALICIOUS_HEADER_PATTERNS:
        if re.search(pattern, headers_text, re.IGNORECASE):
            return True
    return False


def inspect_json(obj: object, score: int = 0) -> int:
    if isinstance(obj, dict):
        for value in obj.values():
            score = inspect_json(value, score)
    elif isinstance(obj, list):
        for item in obj:
            score = inspect_json(item, score)
    elif isinstance(obj, str):
        if re.search(r"union\s+select", obj, re.IGNORECASE):
            score += 100
        for pattern in MALICIOUS_BODY_PATTERNS[:4]:
            if re.search(pattern, obj, re.IGNORECASE):
                score += 25
        for pattern in MALICIOUS_BODY_PATTERNS[4:]:
            if re.search(pattern, obj, re.IGNORECASE):
                score += 20
    return score


def body_score(body: bytes) -> int:
    score = 0
    text = unquote_plus(body.decode("utf-8", errors="ignore"))

    if re.search(r"union\s+select", text, re.IGNORECASE):
        score += 100

    for pattern in MALICIOUS_BODY_PATTERNS[:4]:
        matches = len(re.findall(pattern, text, re.IGNORECASE))
        score += matches * 15

    for pattern in MALICIOUS_BODY_PATTERNS[4:]:
        matches = len(re.findall(pattern, text, re.IGNORECASE))
        score += matches * 10

    if len(text) > 1000:
        score += 10

    try:
        payload = json.loads(text)
        score = inspect_json(payload, score)
    except json.JSONDecodeError:
        pass

    return score


async def run_waf_checks(request: Request, body: bytes | None = None) -> WAFResult:
    if header_check(request):
        return WAFResult(blocked=True, score=BLOCK_SCORE, reason="WAF headers", block_type="headers")

    if body is None:
        body = await request.body()

    score = body_score(body)

    if score >= BLOCK_SCORE:
        return WAFResult(blocked=True, score=score, reason="WAF body", block_type="body")

    if score >= ALERT_SCORE:
        return WAFResult(alert=True, score=score, reason=f"WAF alert score={score}")

    return WAFResult(score=score, reason="OK")
