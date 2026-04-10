from datetime import datetime, timedelta
from typing import Any, Dict

from fastapi import Depends, Header, HTTPException
from jose import JWTError, jwt
from pydantic import BaseModel

SECRET_KEY = 'supersecretkey'
ALGORITHM = 'HS256'
API_KEY = 'hackathon2026'
ACCESS_TOKEN_EXPIRE_MINUTES = 60

class LoginRequest(BaseModel):
    username: str
    password: str


def validate_api_key(x_api_key: str = Header(None)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail='Invalid API key')
    return x_api_key


def create_access_token(payload: Dict[str, Any]) -> str:
    to_encode = payload.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({'exp': expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def authenticate_jwt(authorization: str = Header(None)):
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail='Missing authorization token')

    token = authorization.split(' ', 1)[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail='Invalid token')
