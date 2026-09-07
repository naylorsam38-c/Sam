"""Authentication primitives shared by the control API.

Single-user personal system: one bearer token (JWT, HMAC-signed with
AUTH_SECRET) issued at login. Every mutating endpoint requires it
(spec section 15).
"""

from __future__ import annotations

import hashlib
import hmac
import time
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from workstation_core.config import get_settings

JWT_ALGORITHM = "HS256"

# bcrypt truncates at 72 bytes; reject longer input explicitly rather than
# silently truncating (a caller-visible error beats a password that
# quietly loses its tail characters).
_BCRYPT_MAX_BYTES = 72


def hash_password(password: str) -> str:
    encoded = password.encode("utf-8")
    if len(encoded) > _BCRYPT_MAX_BYTES:
        raise ValueError(f"password must be at most {_BCRYPT_MAX_BYTES} bytes")
    return bcrypt.hashpw(encoded, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(user_id: str, username: str) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "username": username,
        "iat": now,
        "exp": now + timedelta(minutes=settings.auth_token_ttl_minutes),
    }
    return jwt.encode(payload, settings.auth_secret, algorithm=JWT_ALGORITHM)


class InvalidTokenError(Exception):
    pass


def decode_access_token(token: str) -> dict:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.auth_secret, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError as exc:
        raise InvalidTokenError(str(exc)) from exc


# --- Control-plane <-> local execution agent channel -----------------------
#
# Requests to the local agent are signed with HMAC-SHA256 over a canonical
# string using EXECUTION_AGENT_TOKEN as the shared secret, with a timestamp
# to prevent replay. The agent independently verifies this signature; a
# compromised or malicious cloud LLM cannot forge it without the secret.

MAX_REQUEST_AGE_SECONDS = 60


def sign_agent_request(request_id: str, operation: str, timestamp: int, token: str) -> str:
    message = f"{request_id}:{operation}:{timestamp}".encode()
    return hmac.new(token.encode(), message, hashlib.sha256).hexdigest()


def verify_agent_request(
    request_id: str, operation: str, timestamp: int, signature: str, token: str
) -> tuple[bool, str]:
    if abs(time.time() - timestamp) > MAX_REQUEST_AGE_SECONDS:
        return False, "request timestamp outside allowed window (possible replay)"
    expected = sign_agent_request(request_id, operation, timestamp, token)
    if not hmac.compare_digest(expected, signature):
        return False, "invalid signature"
    return True, "ok"
