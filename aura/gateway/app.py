"""
Session gateway (spec §7 session gateway, §17 only public surface).

Responsibilities:
  - authenticate the calling client, then issue a short-lived scoped token
  - rate-limit + isolate sessions
  - health + metrics endpoints, reporting the REAL resolved providers
  - hand a verified client to a Session bound to a Transport

Model, render and Command Desk ports are NOT exposed here. Run behind TLS.
"""
from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse

from ..config import Config
from ..worker import log
from . import auth, rtc
from .security import RateLimiter, SessionRegistry

DEV = os.getenv("AURA_DEV") == "1"
SECRET = auth.validate_secret(os.getenv("AURA_TOKEN_SECRET", ""), dev=DEV)
cfg = Config.load(os.getenv("AURA_CONFIG", "config/aura.yaml"))
app = FastAPI(title="Aura Gateway", version="1.1.0")
_rl = RateLimiter(rate=1.0, burst=5)
_reg = SessionRegistry(max_sessions=int(os.getenv("AURA_MAX_SESSIONS", "1")))

if DEV:
    log("gateway", "warn", "AURA_DEV=1 — client authentication is BYPASSED and "
                           "the signing secret is unchecked. Never use in production.")


def _rate_key(req: Request) -> str:
    """Rate-limit on the transport peer, not on a client-supplied header — a
    header-keyed bucket is trivially evaded by changing the header."""
    return req.client.host if req.client else "anon"


@app.post("/v1/session")
async def create_session(req: Request):
    """Authenticate the calling app, return a signed token + room. The app then
    connects to the transport with this token."""
    if not _rl.allow(_rate_key(req)):
        raise HTTPException(429, "rate limited")
    try:
        user_id = auth.authenticate_client(
            req.headers.get("x-api-key"), req.headers.get("x-user-id"), dev=DEV)
    except auth.AuthError as e:
        raise HTTPException(401, str(e))

    tok = auth.issue(SECRET, user_id, ttl_s=120)
    try:
        _reg.claim(tok["room"], user_id)
    except PermissionError as e:
        raise HTTPException(403, str(e))
    except RuntimeError as e:
        # capacity is an availability condition, not a server bug
        raise HTTPException(503, str(e))
    return JSONResponse({"token": tok["token"], "room": tok["room"],
                         "transport_url": cfg.transport.url,
                         "expires_at": tok["expires_at"]})


@app.post("/v1/session/verify")
async def verify_session(req: Request):
    body = await req.json()
    try:
        payload = auth.verify(SECRET, body.get("token", ""))
    except auth.TokenError as e:
        raise HTTPException(401, str(e))
    if not _reg.authorize(payload["room"], payload["uid"]):
        raise HTTPException(403, "room not owned by user")
    return payload


app.include_router(rtc.router)          # POST /v1/rtc/offer (self-hosted WebRTC)


@app.get("/healthz")
async def health():
    h = rtc.health()
    workers = h.get("workers", {})
    ok = all(workers.values()) if workers else True
    return {"status": "ok" if ok else "degraded", "version": "1.1.0",
            "dev_mode": DEV, **h}


@app.get("/metrics")
async def metrics():
    lines = rtc.metrics_lines()
    lines.append(f"aura_gateway_sessions {_reg.count}")
    return PlainTextResponse("\n".join(lines) + "\n")
