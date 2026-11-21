"""Password hashing and JWT helpers. Pure functions, no database access."""
import hashlib
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt

from .config import settings
from .exceptions import Unauthorized

ALGORITHM = "HS256"
ACCESS = "access"
REFRESH = "refresh"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def ensure_utc(dt: datetime) -> datetime:
    """SQLite returns naive datetimes; treat them as UTC."""
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=settings.bcrypt_rounds)).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except ValueError:
        return False


# A valid hash used to burn the same CPU time when the e-mail is unknown (anti user-enumeration timing).
DUMMY_HASH = bcrypt.hashpw(b"dummy-password", bcrypt.gensalt(rounds=settings.bcrypt_rounds)).decode()


def hash_token(token: str) -> str:
    """Refresh tokens are stored hashed (SHA-256) so a DB leak does not leak usable tokens."""
    return hashlib.sha256(token.encode()).hexdigest()


def _encode(claims: dict[str, Any]) -> str:
    return jwt.encode(claims, settings.secret_key, algorithm=ALGORITHM)


def create_access_token(user_id: int, roles: list[str]) -> tuple[str, int]:
    """Returns (token, expires_in_seconds)."""
    now = utcnow()
    ttl = timedelta(minutes=settings.access_token_minutes)
    token = _encode({
        "sub": str(user_id), "roles": roles, "type": ACCESS,
        "iat": now, "exp": now + ttl, "jti": uuid.uuid4().hex,
    })
    return token, int(ttl.total_seconds())


@dataclass
class RefreshTokenData:
    token: str
    jti: str
    expires_at: datetime


def create_refresh_token(user_id: int) -> RefreshTokenData:
    now = utcnow()
    exp = now + timedelta(days=settings.refresh_token_days)
    jti = uuid.uuid4().hex
    token = _encode({"sub": str(user_id), "type": REFRESH, "iat": now, "exp": exp, "jti": jti})
    return RefreshTokenData(token, jti, exp)


def decode_token(token: str, expected_type: str) -> dict[str, Any]:
    """Verify signature/expiry/required claims and that the token has the expected type."""
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[ALGORITHM],
            options={"require": ["sub", "exp", "iat", "jti", "type"]},
        )
    except jwt.InvalidTokenError as exc:
        raise Unauthorized("Invalid or expired token") from exc
    if payload.get("type") != expected_type:
        raise Unauthorized(f"Wrong token type: expected a {expected_type} token")
    try:
        int(payload["sub"])
    except (TypeError, ValueError) as exc:
        raise Unauthorized("Invalid token subject") from exc
    return payload
