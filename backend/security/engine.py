import time
from collections import deque
from typing import Dict
from fastapi import Request

from security.detector import detect_attacks

BLOCK_THRESHOLD = 8
ALERT_THRESHOLD = 4
BUSINESS_LOGIC_ALERT_THRESHOLD = 50
BUSINESS_LOGIC_BLOCK_THRESHOLD = 70
BUSINESS_LOGIC_WINDOW = 60
_user_request_log: Dict[int, deque] = {}
CRITICAL_ATTACKS = {'sql_injection', 'command_injection', 'ssrf', 'path_traversal'}


def _normalize_reasons(reasons):
    unique = []
    seen = set()
    for reason in reasons:
        if reason not in seen:
            seen.add(reason)
            unique.append(reason)
    return unique


def evaluate_request(request: Request, body: bytes, token_payload: Dict[str, object]) -> Dict[str, object]:
    result = detect_attacks(request, body)
    score = result['score']
    reasons = _normalize_reasons(result['reasons'])

    if any(reason in CRITICAL_ATTACKS for reason in reasons):
        return {
            'status': 'block',
            'score': score,
            'reasons': reasons,
        }

    user_id = token_payload.get('user_id')
    if isinstance(user_id, int):
        now = time.time()
        window = _user_request_log.setdefault(user_id, deque())
        while window and now - window[0] > BUSINESS_LOGIC_WINDOW:
            window.popleft()
        window.append(now)

        if len(window) > BUSINESS_LOGIC_BLOCK_THRESHOLD:
            if 'business_logic_abuse' not in reasons:
                reasons.append('business_logic_abuse')
            score += 5
            return {
                'status': 'block',
                'score': score,
                'reasons': reasons,
            }
        if len(window) > BUSINESS_LOGIC_ALERT_THRESHOLD:
            if 'business_logic_abuse' not in reasons:
                reasons.append('business_logic_abuse')
            score += 2

    if 'xss' in reasons and score < BLOCK_THRESHOLD:
        status = 'alert'
    elif score >= BLOCK_THRESHOLD:
        status = 'block'
    elif score >= ALERT_THRESHOLD:
        status = 'alert'
    else:
        status = 'allow'

    return {
        'status': status,
        'score': score,
        'reasons': reasons,
    }
