import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from .db import get_config, set_config

TOKEN_EXPIRE_DAYS = 30
ALGORITHM = "HS256"
_SECRET_KEY = "auth_secret"
_PASSWORD_HASH_KEY = "auth_password_hash"
_PBKDF2_ITERATIONS = 260000

bearer = HTTPBearer(auto_error=False)


def _hash_password(password: str) -> str:
    salt = os.urandom(32)
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _PBKDF2_ITERATIONS)
    return salt.hex() + ":" + key.hex()


def _check_password(password: str, stored: str) -> bool:
    try:
        salt_hex, key_hex = stored.split(":")
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(key_hex)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _PBKDF2_ITERATIONS)
        return hmac.compare_digest(expected, actual)
    except Exception:
        return False


def _get_secret() -> str:
    secret = get_config(_SECRET_KEY)
    if not secret:
        secret = secrets.token_hex(64)
        set_config(_SECRET_KEY, secret)
    return secret


def is_password_set() -> bool:
    return get_config(_PASSWORD_HASH_KEY) is not None


def set_password(password: str) -> None:
    set_config(_PASSWORD_HASH_KEY, _hash_password(password))


def verify_password(password: str) -> bool:
    stored = get_config(_PASSWORD_HASH_KEY)
    if not stored:
        return False
    return _check_password(password, stored)


def create_token() -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=TOKEN_EXPIRE_DAYS)
    return jwt.encode({"exp": expire}, _get_secret(), algorithm=ALGORITHM)


def _decode_token(token: str) -> bool:
    try:
        jwt.decode(token, _get_secret(), algorithms=[ALGORITHM])
        return True
    except JWTError:
        return False


def require_auth(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> None:
    if credentials is None or not _decode_token(credentials.credentials):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未登录或登录已过期",
            headers={"WWW-Authenticate": "Bearer"},
        )
