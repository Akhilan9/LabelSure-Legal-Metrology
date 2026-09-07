from datetime import datetime, timedelta, timezone
from functools import lru_cache
import secrets

import jwt
from fastapi import HTTPException
from pwdlib import PasswordHash

from app.core.config import Settings

password_hasher = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


@lru_cache(maxsize=1)
def dummy_hash() -> str:
    return hash_password(secrets.token_urlsafe(32))


def verify_password(password: str, hashed: str) -> bool:
    return password_hasher.verify(password, hashed)


def signing_key(settings: Settings) -> str:
    if settings.jwt_secret is None:
        raise HTTPException(503, "Authentication is not configured. Contact the administrator.")
    return settings.jwt_secret.get_secret_value()


def issue_token(user_id: str, settings: Settings) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode({
        "sub": user_id, "iat": now, "nbf": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
        "iss": "labelsure-api", "aud": "labelsure-clients", "type": "access",
        "jti": secrets.token_hex(16),
    }, signing_key(settings), algorithm=settings.jwt_algorithm)


def decode_token(token: str, settings: Settings) -> dict:
    claims = jwt.decode(token, signing_key(settings), algorithms=[settings.jwt_algorithm],
                        issuer="labelsure-api", audience="labelsure-clients",
                        options={"require": ["sub", "exp", "iat", "nbf", "iss", "aud", "type", "jti"]})
    if claims["type"] != "access" or not isinstance(claims["sub"], str):
        raise jwt.InvalidTokenError("Invalid access token")
    return claims
