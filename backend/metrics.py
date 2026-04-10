from collections import defaultdict
from typing import Dict, List, Optional

_metrics = {
    'total_requests': 0,
    'blocked_requests': 0,
    'alerts': 0,
    'requests_per_ip': {},
    'requests_per_user': {},
    'blocked_reasons': {},
    'attack_types': {},
}
_ip_totals = defaultdict(int)
_user_totals = defaultdict(int)
_blocked_reasons = defaultdict(int)
_attack_types = defaultdict(int)


def record_request() -> None:
    _metrics['total_requests'] += 1


def record_block() -> None:
    _metrics['blocked_requests'] += 1


def record_alert() -> None:
    _metrics['alerts'] += 1


def record_ip_request(ip: str) -> None:
    _ip_totals[ip] += 1
    _metrics['requests_per_ip'] = dict(_ip_totals)


def record_user_request(user_id: Optional[int]) -> None:
    if user_id is None:
        return
    _user_totals[user_id] += 1
    _metrics['requests_per_user'] = dict(_user_totals)


def record_block_reason(reason: str) -> None:
    _blocked_reasons[reason] += 1
    _metrics['blocked_reasons'] = dict(_blocked_reasons)


def record_attack_types(reasons: List[str]) -> None:
    for reason in reasons:
        _attack_types[reason] += 1
    _metrics['attack_types'] = dict(_attack_types)


def get_metrics() -> Dict[str, object]:
    return {
        'total_requests': _metrics['total_requests'],
        'blocked_requests': _metrics['blocked_requests'],
        'alerts': _metrics['alerts'],
        'requests_per_ip': dict(_ip_totals),
        'requests_per_user': dict(_user_totals),
        'blocked_reasons': dict(_blocked_reasons),
        'attack_types': dict(_attack_types),
    }
