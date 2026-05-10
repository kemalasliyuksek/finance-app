"""JWT token oluşturma/doğrulama ve password yardımcıları."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import bcrypt as _bcrypt
import jwt

from src.config import settings


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return _bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8"),
    )


def hash_password(password: str) -> str:
    return _bcrypt.hashpw(
        password.encode("utf-8"), _bcrypt.gensalt(),
    ).decode("utf-8")


def create_access_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.jwt_access_token_expire_minutes,
    )
    payload = {"sub": subject, "exp": expire, "iat": datetime.now(timezone.utc), "type": "access"}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.jwt_refresh_token_expire_days,
    )
    payload = {"sub": subject, "exp": expire, "iat": datetime.now(timezone.utc), "type": "refresh"}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def verify_token(token: str, expected_type: str = "access") -> dict:
    """Token doğrula. Geçersizse jwt.PyJWTError fırlatır."""
    payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    if payload.get("type") != expected_type:
        raise jwt.InvalidTokenError(f"Expected token type '{expected_type}', got '{payload.get('type')}'")
    return payload
