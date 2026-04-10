import hashlib
import time
from uuid import uuid4

from core.config import BLOCK_THRESHOLD, BLOCK_WINDOW_SECONDS

abuse: dict[str, list[float]] = {}


def record_abuse(ip: str) -> int:
    now = time.time()
    ip_list = abuse.setdefault(ip, [])
    ip_list = [timestamp for timestamp in ip_list if timestamp > now - BLOCK_WINDOW_SECONDS]
    ip_list.append(now)
    abuse[ip] = ip_list
    return len(ip_list)


def get_abuse_score(ip: str) -> int:
    now = time.time()
    return len([timestamp for timestamp in abuse.get(ip, []) if timestamp > now - BLOCK_WINDOW_SECONDS])


def build_abuse_headers(score: int) -> dict[str, str]:
    return {"X-Abuse-Score": str(score), "X-Request-ID": str(uuid4())}


def fingerprint_request(ip: str, method: str, path: str, body: bytes | None = None) -> str:
    body_digest = hashlib.sha256(body or b"").hexdigest()
    payload = f"{ip}:{method}:{path}:{body_digest}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def should_block_ip(score: int) -> bool:
    return score >= BLOCK_THRESHOLD
