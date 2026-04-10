from typing import Any

fingerprints: dict[str, Any] = {}
blocked_ips: dict[str, int] = {}


def get_fingerprint(key: str) -> Any:
    return fingerprints.get(key)


def set_fingerprint(key: str, value: Any) -> None:
    fingerprints[key] = value


def is_ip_blocked(ip: str) -> bool:
    return blocked_ips.get(ip, 0) > 0


def block_ip(ip: str) -> None:
    blocked_ips[ip] = blocked_ips.get(ip, 0) + 1


def get_blocked_ips() -> dict[str, int]:
    return dict(blocked_ips)
