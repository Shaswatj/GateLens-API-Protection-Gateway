import time
from typing import Any

from core.config import DEMO_MODE

fingerprints: dict[str, Any] = {}
blocked_ips: dict[str, float] = {}  # Maps IP to expiration timestamp

# Threat scoring system (NEW - non-breaking addition)
ip_scores: dict[str, int] = {}  # Maps IP to threat score
ip_last_seen: dict[str, float] = {}  # Maps IP to last activity timestamp
THREAT_SCORE_THRESHOLD = 10  # Block if score >= this value
SCORE_DECAY_TIMEOUT = 10  # Seconds of inactivity before score decay

# Block timeout based on mode: 10 seconds for demo, 300 seconds for production
BLOCK_TIMEOUT_SECONDS = 10 if DEMO_MODE else 300


def get_fingerprint(key: str) -> Any:
    return fingerprints.get(key)


def set_fingerprint(key: str, value: Any) -> None:
    fingerprints[key] = value


def is_ip_blocked(ip: str) -> bool:
    if ip not in blocked_ips:
        return False
    
    # Check if block has expired
    if time.time() > blocked_ips[ip]:
        del blocked_ips[ip]  # Remove expired block
        return False
    
    return True


def block_ip(ip: str) -> None:
    """Block an IP for BLOCK_TIMEOUT_SECONDS duration."""
    blocked_ips[ip] = time.time() + BLOCK_TIMEOUT_SECONDS


def get_blocked_ips() -> dict[str, float]:
    # Clean up expired blocks
    current_time = time.time()
    expired = [ip for ip, exp_time in blocked_ips.items() if current_time > exp_time]
    for ip in expired:
        del blocked_ips[ip]
    
    return dict(blocked_ips)


def clear_ip(ip: str) -> bool:
    """Remove an IP from the blocked list.
    
    Returns True if IP was blocked and cleared, False if IP wasn't blocked.
    """
    if ip in blocked_ips:
        del blocked_ips[ip]
        return True
    return False


def clear_all_blocked_ips() -> int:
    """Clear all blocked IPs. Returns the number of IPs cleared."""
    count = len(blocked_ips)
    blocked_ips.clear()
    return count


# ============================================
# THREAT SCORING FUNCTIONS (NEW SYSTEM)
# ============================================

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
    Localhost (127.0.0.1) is never blocked permanently.
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
