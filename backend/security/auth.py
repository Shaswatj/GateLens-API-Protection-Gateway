from fastapi import Header, HTTPException, Request
from jose import JWTError, jwt
from pydantic import BaseModel

from core.config import API_KEY, SECRET_KEY, ALGORITHM, USER_TIERS


class LoginRequest(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as error:
        raise HTTPException(status_code=401, detail="Invalid token") from error


async def authenticate_request(request: Request) -> dict:
    auth_header = request.headers.get("authorization")
    if not auth_header or not auth_header.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = auth_header.split(" ", 1)[1]
    payload = decode_token(token)
    request.state.decoded_token = payload
    return payload


def verify_token(request: Request) -> dict:
    token_state = getattr(request.state, "decoded_token", None)
    if token_state is not None:
        return token_state

    auth_header = request.headers.get("authorization")
    if not auth_header or not auth_header.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = auth_header.split(" ", 1)[1]
    payload = decode_token(token)
    request.state.decoded_token = payload
    return payload


def verify_api_key(x_api_key: str = Header(...)) -> None:
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")


def get_user_tier(token: dict) -> str:
    sub = token.get("sub", "")
    if sub in {"premium", "admin"}:
        return "premium"
    return "free"


