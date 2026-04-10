import logging
from collections import deque
from datetime import datetime, timedelta
from typing import Any, Dict

from .config import LOGS_MAX_SIZE

logging.basicConfig(filename="gateway.log", level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

logs: deque[dict] = deque(maxlen=LOGS_MAX_SIZE)
waf_blocked_logs: deque[dict] = deque(maxlen=10)
metrics: Dict[str, Any] = {
    "total_requests": 0,
    "total_blocked": 0,
    "blocked_requests": 0,
    "allowed_requests": 0,
    "waf_blocked": 0,
    "response_times": deque(maxlen=100),
}
request_counters: Dict[str, int] = {"free": 0, "premium": 0}


def append_log(entry: dict) -> None:
    logs.append(entry)


def append_waf_block(log_entry: dict) -> None:
    waf_blocked_logs.append(log_entry)
    logs.append(log_entry)


def record_response_time(elapsed_ms: float) -> None:
    metrics["response_times"].append(elapsed_ms)


def increment_tier_counter(tier: str) -> None:
    request_counters[tier] = request_counters.get(tier, 0) + 1


def record_blocked_request(elapsed_ms: float, is_waf: bool = False) -> None:
    metrics["total_requests"] += 1
    metrics["total_blocked"] += 1
    metrics["blocked_requests"] += 1
    if is_waf:
        metrics["waf_blocked"] += 1
    record_response_time(elapsed_ms)


def record_allowed_request(elapsed_ms: float, alert: bool = False) -> None:
    metrics["total_requests"] += 1
    record_response_time(elapsed_ms)
    if not alert:
        metrics["allowed_requests"] += 1


def get_average_response_time() -> float:
    response_times = metrics["response_times"]
    if not response_times:
        return 0.0
    return sum(response_times) / len(response_times)


def get_dashboard_payload() -> dict:
    return {
        "total_requests": metrics["total_requests"],
        "total_blocked": metrics["total_blocked"],
        "blocked_requests": metrics["blocked_requests"],
        "allowed_requests": metrics["allowed_requests"],
        "waf_blocked": metrics["waf_blocked"],
        "avg_response_time": round(get_average_response_time(), 2),
        "requests_this_minute": len(
            [log for log in logs if datetime.fromisoformat(log["time"]) > datetime.now() - timedelta(minutes=1)]
        ),
        "rate_limit": 25,
        "logs": list(logs)[-50:],
    }


def get_alerts_payload(abuse_data: dict) -> dict:
    top_abusers = sorted(
        [(ip, len(timestamps)) for ip, timestamps in abuse_data.items()],
        key=lambda x: x[1],
        reverse=True,
    )[:5]

    alert_counts: dict[str, int] = {}
    for log in logs:
        if log.get("reason", "").startswith("WAF alert"):
            ip = log.get("ip")
            alert_counts[ip] = alert_counts.get(ip, 0) + 1

    combined: dict[str, int] = {}
    for ip, count in [(ip, len(timestamps)) for ip, timestamps in abuse_data.items()]:
        combined[ip] = combined.get(ip, 0) + count
    for ip, count in alert_counts.items():
        combined[ip] = combined.get(ip, 0) + count

    top_combined = sorted(combined.items(), key=lambda x: x[1], reverse=True)[:5]
    abusive_ips = [
        {"ip": ip, "block_count": count, "last_block": None}
        for ip, count in top_combined
    ]

    return {
        "top_abusive_ips": abusive_ips,
        "recent_waf_blocks": list(waf_blocked_logs),
        "total_abuse_ips": len(combined),
        "total_waf_blocked_today": metrics["waf_blocked"],
    }


def get_waf_alerts_payload(abuse_data: dict) -> dict:
    now = datetime.now()
    window_start = now - timedelta(seconds=300)

    waf_entries: list[dict] = []
    for log in reversed(list(logs)):
        is_block = log.get("status") == 403 and log.get("reason", "").startswith("WAF")
        is_alert = log.get("reason", "").startswith("WAF") and log.get("status") == 200
        if is_block or is_alert:
            waf_entries.append(
                {
                    "time": log.get("time"),
                    "ip": log.get("ip"),
                    "endpoint": log.get("endpoint"),
                    "reason": log.get("reason"),
                    "status": log.get("status"),
                }
            )
            if len(waf_entries) >= 15:
                break

    abuse_count: dict[str, int] = {}
    for ip, timestamps in abuse_data.items():
        recent_blocks = [ts for ts in timestamps if ts > window_start.timestamp()]
        if recent_blocks:
            abuse_count[ip] = len(recent_blocks)

    top_abuse_ips = sorted(
        [{"ip": ip, "block_count": count} for ip, count in abuse_count.items()],
        key=lambda x: x["block_count"],
        reverse=True,
    )[:5]

    return {
        "last_waf_blocks": waf_entries,
        "top_abuse_ips": top_abuse_ips,
    }


def get_metrics_payload(abuse_data: dict) -> dict:
    blocked_by_reason: dict[str, int] = {}
    for log in logs:
        if log.get("status", 0) >= 400:
            reason = log.get("reason", "unknown")
            blocked_by_reason[reason] = blocked_by_reason.get(reason, 0) + 1

    avg_response_time = round(get_average_response_time(), 2)
    return {
        "total_requests": metrics["total_requests"],
        "total_blocked": metrics["total_blocked"],
        "allowed_requests": metrics["allowed_requests"],
        "avg_response_time_ms": avg_response_time,
        "tiers": request_counters,
        "abuse_ip_count": len(abuse_data),
        "blocked_ips": {ip: len(ts) for ip, ts in abuse_data.items()},
        "blocked_by_reason": blocked_by_reason,
        "logs": list(logs)[-50:],
    }
