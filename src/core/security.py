"""
src/core/security.py
--------------------
Cryptographic utilities — password hashing and JWT token management.

Why bcrypt directly instead of passlib?
  passlib 1.7.4 (last release: 2020, unmaintained) has a known incompatibility
  with bcrypt >= 4.0.0: it passes the password as a str instead of bytes, which
  triggers bcrypt 4.x's strict 72-byte check even for short passwords.
  Using bcrypt directly avoids this entirely and keeps the dependency simpler.

Password hashing — bcrypt:
  - encode() converts str → bytes (bcrypt operates on bytes)
  - gensalt() generates a cryptographically random 128-bit salt per hash
  - checkpw() is timing-safe: always runs the full Feistel network regardless
    of where the mismatch occurs, preventing timing-based side channels

JWT (JSON Web Tokens):
  - access_token  short-lived (30 min default) — sent with every API request
  - refresh_token long-lived  (7 days default) — stored securely, used only
                                                  to mint new access tokens
  - 'type' claim: guards against using a refresh token as an access token
  - Always use timezone-aware UTC datetimes in production
"""

from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from jose import jwt

from src.config.settings import settings


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

def hash_password(plain_password: str) -> str:
    """Hash a password with bcrypt. Store the result — never the raw password."""
    return bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Timing-safe comparison between a plain password and its stored bcrypt hash.
    bcrypt.checkpw always runs the full computation — no short-circuit on mismatch.
    """
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


# ---------------------------------------------------------------------------
# JWT token helpers
# ---------------------------------------------------------------------------

def create_access_token(subject: str | Any, expires_delta: timedelta | None = None) -> str:
    """Create a short-lived JWT access token. 'sub' holds the user ID as a string."""
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = {"sub": str(subject), "exp": expire, "type": "access"}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(subject: str | Any) -> str:
    """Create a long-lived JWT refresh token."""
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {"sub": str(subject), "exp": expire, "type": "refresh"}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict:
    """
    Decode and cryptographically verify a JWT.
    Raises jose.JWTError (or subclass) on any failure:
      ExpiredSignatureError — token is past its 'exp'
      JWTError              — signature invalid / malformed token
    """
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
