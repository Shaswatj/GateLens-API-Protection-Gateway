from contextvars import ContextVar
from typing import Optional

from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Request
from jose import JWTError

from core.config import RATE_LIMIT, USER_TIERS
from security.auth import decode_token, get_user_tier

current_request: ContextVar[Optional[Request]] = ContextVar("current_request", default=None)
limiter = Limiter(key_func=get_remote_address)


def set_current_request(request: Request):
    return current_request.set(request)


def reset_current_request(token):
    current_request.reset(token)


def get_current_request() -> Optional[Request]:
    return current_request.get()


def get_rate_limit_for_request(request: Request) -> str:
    token = getattr(request.state, "decoded_token", None)
    if token is not None:
        return USER_TIERS.get(get_user_tier(token), RATE_LIMIT)

    auth_header = request.headers.get("authorization", "")
    if not auth_header.lower().startswith("bearer "):
        return RATE_LIMIT

    token = auth_header.split(" ", 1)[1]
    try:
        payload = decode_token(token)
        request.state.decoded_token = payload
        return USER_TIERS.get(get_user_tier(payload), RATE_LIMIT)
    except JWTError:
        return RATE_LIMIT


def check_rate_limit(key: str) -> str:
    request = get_current_request()
    if request is not None:
        return get_rate_limit_for_request(request)
    return RATE_LIMIT
