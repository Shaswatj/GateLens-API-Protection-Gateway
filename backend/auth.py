from datetime import datetime, timedelta
from typing import Any, Dict

from fastapi import Header, HTTPException
from jose import JWTError, jwt
from pydantic import BaseModel

from core.config import API_KEY, ALGORITHM, SECRET_KEY, ACCESS_TOKEN_EXPIRE_MINUTES

class LoginRequest(BaseModel):
    username: str
    password: str


def validate_api_key(x_api_key: str = Header(None, alias='X-API-Key')):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail='Invalid API key')
    return x_api_key


def create_access_token(payload: Dict[str, Any]) -> str:
    to_encode = payload.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({'exp': expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def authenticate_jwt(authorization: str = Header(None, alias='Authorization')):
    print('AUTH HEADER:', authorization)
    if not authorization:
        raise HTTPException(status_code=401, detail='Missing authorization token')

    authorization = authorization.strip()
    if not authorization.lower().startswith('bearer '):
        raise HTTPException(status_code=401, detail='Missing authorization token')

    token = authorization.split(' ', 1)[1].strip()
    print('TOKEN:', token)
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        print('JWT PAYLOAD:', payload)
        return payload
    except JWTError as e:
        print('JWT ERROR:', str(e))
        raise HTTPException(status_code=401, detail='Invalid token')
