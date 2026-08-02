"""
Session authentication and short-lived signed tokens (spec §17, §18).

Two layers, and they do different jobs:

  authenticate_client()  proves WHO is asking, before any token is issued.
  issue()/verify()       short-lived HMAC token scoped to one room + one user.

The original build had only the second layer: `/v1/session` minted a valid token
for anyone who sent an `x-user-id` header. A signed token is worthless if the
thing that signs it will sign anything — so client credentials are now required
and the header alone is no longer identity.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
import uuid

DEFAULT_SECRET = "change-me-in-prod"
MIN_SECRET_LEN = 32


class TokenError(Exception):
    pass


class AuthError(Exception):
    pass


class InsecureConfiguration(RuntimeError):
    """Raised at startup for a configuration that must never reach production."""


# ── startup validation ──────────────────────────────────────────────────────
def validate_secret(secret: str, *, dev: bool = False) -> str:
    """Refuse to run with a guessable signing secret.

    Failing at startup is the point. A default secret does not announce itself
    at runtime — every token verifies perfectly, and anyone who has read this
    open-source repo can mint one.
    """
    if dev:
        return secret
    if not secret or secret == DEFAULT_SECRET:
        raise InsecureConfiguration(
            "AURA_TOKEN_SECRET is unset or still the default. Generate one with "
            "`openssl rand -hex 32` and set it in the environment. Refusing to "
            "start: every token this signs would be forgeable from the public repo.")
    if len(secret) < MIN_SECRET_LEN:
        raise InsecureConfiguration(
            f"AURA_TOKEN_SECRET is {len(secret)} chars; need >= {MIN_SECRET_LEN}.")
    return secret


# ── layer 1: who is asking ──────────────────────────────────────────────────
def _client_table() -> dict[str, str]:
    """Parse AURA_API_KEYS as `key:user_id,key2:user2`.

    Deliberately simple: one shared secret per calling application, mapped to the
    user id it may act as. Swap this for OIDC/JWT when you have an IdP — the rest
    of the gateway only cares that `authenticate_client` returns a user id.
    """
    raw = os.getenv("AURA_API_KEYS", "").strip()
    table: dict[str, str] = {}
    for pair in raw.split(","):
        pair = pair.strip()
        if not pair:
            continue
        key, _, user = pair.partition(":")
        if key and user:
            table[key] = user
    return table


def authenticate_client(api_key: str | None, claimed_user: str | None,
                        *, dev: bool = False) -> str:
    """Return the authenticated user id, or raise AuthError.

    In dev mode the claimed header is trusted so the local demo still runs, and
    the caller logs that loudly. Everywhere else a valid API key is required and
    the user id comes from the key's mapping — never from the caller-supplied
    header, which a client can set to anything.
    """
    if dev:
        return claimed_user or "dev-user"
    table = _client_table()
    if not table:
        raise AuthError(
            "no client credentials configured. Set AURA_API_KEYS="
            "'<key>:<user_id>' (or run with AURA_DEV=1 for local development).")
    if not api_key:
        raise AuthError("missing API key")

    # Compare against every entry so a wrong key does not return measurably
    # faster than a right one.
    matched: str | None = None
    for known, user in table.items():
        if hmac.compare_digest(api_key, known):
            matched = user
    if matched is None:
        raise AuthError("invalid API key")
    if claimed_user and claimed_user != matched:
        raise AuthError(f"API key is authorised for '{matched}', not '{claimed_user}'")
    return matched


# ── layer 2: short-lived scoped tokens ──────────────────────────────────────
def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def issue(secret: str, user_id: str, ttl_s: int = 120) -> dict:
    now = int(time.time())
    room = f"aura-{user_id}-{uuid.uuid4().hex[:8]}"
    payload = {"uid": user_id, "room": room, "iat": now, "exp": now + ttl_s,
               "jti": uuid.uuid4().hex}
    body = _b64(json.dumps(payload, separators=(",", ":")).encode())
    sig = _b64(hmac.new(secret.encode(), body.encode(), hashlib.sha256).digest())
    return {"token": f"{body}.{sig}", "room": room, "expires_at": payload["exp"]}


def verify(secret: str, token: str) -> dict:
    try:
        body, sig = token.split(".")
    except ValueError as e:
        raise TokenError("malformed token") from e
    expect = _b64(hmac.new(secret.encode(), body.encode(), hashlib.sha256).digest())
    if not hmac.compare_digest(sig, expect):
        raise TokenError("bad signature")
    try:
        payload = json.loads(_unb64(body))
    except Exception as e:
        raise TokenError("malformed payload") from e
    if int(payload.get("exp", 0)) < int(time.time()):
        raise TokenError("expired")
    for claim in ("uid", "room", "jti"):
        if not payload.get(claim):
            raise TokenError(f"missing claim {claim}")
    return payload
