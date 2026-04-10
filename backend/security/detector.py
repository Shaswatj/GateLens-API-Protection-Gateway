import re
from typing import Any, Dict
from urllib.parse import unquote_plus
from fastapi import Request

from security.rules import RULES


def _safe_decode(value: str) -> str:
    decoded = value
    for _ in range(3):
        try:
            next_value = unquote_plus(decoded)
        except Exception:
            break
        if next_value == decoded:
            break
        decoded = next_value
    return decoded


def _normalize_text(text: str) -> str:
    safe_text = text.replace('\x00', ' ')
    safe_text = safe_text.replace('^', ' ')
    safe_text = safe_text.replace('\r', ' ').replace('\n', ' ').replace('\t', ' ')
    safe_text = _safe_decode(safe_text)
    safe_text = safe_text.lower().strip()
    safe_text = re.sub(r'\s+', ' ', safe_text)
    safe_text = re.sub(r'([^\w\s])\1{2,}', r'\1\1', safe_text)
    return safe_text


def _extract_text(request: Request, body: bytes) -> str:
    parts = [request.url.path or '', request.url.query or '']

    if body:
        try:
            parts.append(body.decode('utf-8', errors='ignore'))
        except Exception:
            parts.append(str(body))

    combined = ' '.join(parts)
    return _normalize_text(combined)


def detect_attacks(request: Request, body: bytes) -> Dict[str, Any]:
    text = _extract_text(request, body)
    score = 0
    reasons = []

    for attack_type, rule in RULES.items():
        for pattern in rule['patterns']:
            if re.search(pattern, text):
                if attack_type not in reasons:
                    reasons.append(attack_type)
                score += rule['score']
                break

    return {'score': score, 'reasons': reasons}
