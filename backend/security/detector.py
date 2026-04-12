import re
from typing import Any, Dict
from urllib.parse import unquote_plus
from fastapi import Request

from security.rules import RULES

# Safe import of ML detector - optional
try:
    from ml.attack_detector import detector as ml_detector
    ML_AVAILABLE = True
except Exception as e:
    print(f"[DETECTOR] Warning: ML detector not available. {e}")
    ML_AVAILABLE = False
    ml_detector = None


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
    safe_text = re.sub(r'/\*.*?\*/', ' ', safe_text)
    safe_text = re.sub(r'(--|#).*?(?:\r|\n|$)', ' ', safe_text)
    safe_text = safe_text.lower().strip()
    safe_text = re.sub(r'\s+', ' ', safe_text)
    safe_text = re.sub(r'([^\w\s])\1{2,}', r'\1\1', safe_text)
    return safe_text


def _extract_text(request: Request, body: bytes) -> str:
    # Extract headers but EXCLUDE Host header (which contains internal localhost)
    headers_text_parts = []
    for name, value in request.headers.items():
        if name.lower() != 'host':  # Skip Host header to avoid false SSRF positives
            headers_text_parts.append(f'{name}:{value}')
    headers_text = ' '.join(headers_text_parts)
    
    parts = [request.url.path or '', request.url.query or '', headers_text]

    if body:
        try:
            parts.append(body.decode('utf-8', errors='ignore'))
        except Exception:
            parts.append(str(body))

    combined = ' '.join(parts)
    return _normalize_text(combined)


def _is_safe_endpoint(path: str) -> bool:
    """Check if this is a common safe endpoint that shouldn't trigger ML false positives"""
    safe_paths = {
        '/users', '/orders', '/products', '/health', '/status', 
        '/api/info', '/api/data', '/api/test', '/admin', '/test-waf',
        '/metrics', '/alerts', '/waf-alerts', '/clear-ip'
    }
    normalized = path.strip('/').lower()
    # Check direct match
    if f'/{normalized}' in safe_paths:
        return True
    # Check prefix match for API-style paths
    for safe in safe_paths:
        if normalized.startswith(safe.strip('/')):
            return True
    return False


def detect_attacks(request: Request, body: bytes) -> Dict[str, Any]:
    """
    Combined rule-based and ML-based attack detection.
    
    Strategy:
    1. Run rule-based detection (existing) - ALWAYS
    2. Run ML-based detection (optional) - if available
    3. Combine scores safely
    4. Fallback to rule-based only if ML fails
    5. Skip ML on safe endpoints to prevent false positives
    """
    text = _extract_text(request, body)
    score = 0
    reasons = []
    is_safe_endpoint = _is_safe_endpoint(request.url.path)

    # Rule-based detection (always runs)
    for attack_type, rule in RULES.items():
        for pattern in rule['patterns']:
            if re.search(pattern, text):
                if attack_type not in reasons:
                    reasons.append(attack_type)
                score += rule['score']
                break

    # ML-based detection (optional, with graceful fallback)
    # SKIP ML on safe endpoints to prevent false positives on /users, /orders, etc.
    if not is_safe_endpoint and ML_AVAILABLE and ml_detector:
        try:
            ml_prediction = ml_detector.predict(text)
            if ml_prediction['is_attack']:
                ml_label = ml_prediction['label']
                confidence = ml_prediction['confidence']
                
                # IMPORTANT: Only trust ML if confidence is very high (>= 0.85)
                # This prevents false positives on normal API paths like /users
                if confidence >= 0.85:
                    # Add ML detection to reasons
                    ml_reason = f"ml_{ml_label}"
                    if ml_reason not in reasons:
                        reasons.append(ml_reason)
                    
                    # Boost score for high-confidence ML detections
                    score += 40  # High confidence attacks from ML
        except Exception as e:
            # Log error but continue - don't break on ML failure
            print(f"[DETECTOR] ML prediction failed (continuing with rule-based): {e}")

    return {'score': score, 'reasons': reasons}
