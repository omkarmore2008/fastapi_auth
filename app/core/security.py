"""Security helpers for hashing, JWT, and token utilities."""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a plaintext password.

    Args:
        password: User plaintext password.
    Returns:
        str: Argon2 password hash.
    """
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify plaintext password against a hash.

    Args:
        password: User plaintext password.
        password_hash: Stored password hash.
    Returns:
        bool: True when password matches hash.
    """
    return pwd_context.verify(password, password_hash)


def hash_token_value(raw_value: str) -> str:
    """Hash sensitive token values before DB storage.

    Args:
        raw_value: Raw token or OTP value.
    Returns:
        str: SHA256 digest string.
    """
    return hashlib.sha256(raw_value.encode("utf-8")).hexdigest()


def generate_secure_token(length: int = 48) -> str:
    """Generate a URL-safe random token.

    Args:
        length: Approximate token entropy length.
    Returns:
        str: URL-safe token string.
    """
    return secrets.token_urlsafe(length)


def generate_numeric_otp(length: int = 6) -> str:
    """Generate numeric one-time password.

    Args:
        length: Number of digits required.
    Returns:
        str: Numeric OTP value.
    """
    return "".join(secrets.choice("0123456789") for _ in range(length))


def create_token_pair(subject: str, session_id: str) -> dict[str, str]:
    """Create signed access and refresh JWTs.

    Args:
        subject: User ID in token subject claim.
        session_id: Refresh session identifier claim.
    Returns:
        dict[str, str]: Access and refresh tokens.
    """
    settings = get_settings()
    now = datetime.now(UTC)
    access_exp = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_exp = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    access_payload: dict[str, Any] = {
        "sub": subject,
        "type": "access",
        "sid": session_id,
        "jti": str(uuid4()),
        "exp": int(access_exp.timestamp()),
        "iat": int(now.timestamp()),
    }
    refresh_payload: dict[str, Any] = {
        "sub": subject,
        "type": "refresh",
        "sid": session_id,
        "jti": str(uuid4()),
        "exp": int(refresh_exp.timestamp()),
        "iat": int(now.timestamp()),
    }
    return {
        "access_token": jwt.encode(access_payload, settings.SECRET_KEY, algorithm="HS256"),
        "refresh_token": jwt.encode(refresh_payload, settings.SECRET_KEY, algorithm="HS256"),
    }


def decode_jwt(token: str) -> dict[str, Any] | None:
    """Decode and validate a JWT.

    Args:
        token: JWT string.
    Returns:
        dict[str, Any] | None: Claims when valid, None otherwise.
    """
    settings = get_settings()
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    except JWTError:
        return None
