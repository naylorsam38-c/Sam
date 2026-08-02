"""
WebRTC signaling (self-hosted, single reliable user — spec §25).

POST /v1/rtc/offer with a browser SDP offer + a valid session token → builds the
avatar pipeline behind a self-hosted aiortc peer connection and returns the SDP
answer. No LiveKit server, no paid service. The pipeline's workers are held so
the gateway can report real health/metrics.
"""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException, Request

from ..config import Config
from ..protocol import State
from ..runtime import build_session

router = APIRouter()

# single active session (one reliable user first)
STATE: dict = {"pc": None, "session": None, "workers": None, "transport": None,
               "uid": None}


def _session_is_live() -> bool:
    """True while a peer connection is actually up. A stale entry from a browser
    that closed without a state change must not lock the slot forever."""
    pc = STATE.get("pc")
    return pc is not None and pc.connectionState not in (
        "failed", "closed", "disconnected")


async def _teardown():
    if STATE["workers"]:
        for w in STATE["workers"].values():
            try:
                await w.stop()
            except Exception:
                pass
    if STATE["pc"]:
        try:
            await STATE["pc"].close()
        except Exception:
            pass
    STATE.update(pc=None, session=None, workers=None, transport=None, uid=None)


@router.post("/v1/rtc/offer")
async def offer(req: Request):
    from aiortc import RTCPeerConnection, RTCSessionDescription
    from ..transport.aiortc_transport import AiortcTransport

    import os
    from . import auth
    body = await req.json()
    if "sdp" not in body or "type" not in body:
        raise HTTPException(400, "missing sdp/type")

    # require a valid short-lived session token (spec §17) unless dev-bypass
    dev = os.getenv("AURA_DEV") == "1"
    uid = "dev-user"
    if not dev:
        secret = os.getenv("AURA_TOKEN_SECRET", "")
        try:
            payload = auth.verify(secret, body.get("token", ""))
        except auth.TokenError:
            raise HTTPException(401, "invalid or missing session token")
        uid = payload["uid"]

    # A live session belongs to the user who started it. Without this check any
    # other token holder could POST an offer and silently evict them mid-call,
    # because the runtime session id was a constant.
    owner = STATE.get("uid")
    if owner is not None and owner != uid and _session_is_live():
        raise HTTPException(409, "session already active for another user")

    await _teardown()                       # replace this user's prior session
    cfg = Config.load()
    pc = RTCPeerConnection()
    transport = AiortcTransport()
    session, workers = await build_session(uid, cfg, transport)
    transport.attach(pc)
    session.sm.to(State.LISTENING)          # ready for the user to speak
    STATE.update(pc=pc, session=session, workers=workers, transport=transport,
                 uid=uid)

    @pc.on("connectionstatechange")
    async def _on_state():
        if pc.connectionState in ("failed", "closed", "disconnected"):
            await _teardown()

    await pc.setRemoteDescription(RTCSessionDescription(body["sdp"], body["type"]))
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)
    return {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}


def health() -> dict:
    """Report the REAL resolved engines, not the configured ones. A stack that
    silently degraded to the CPU fallback looks identical to a healthy one until
    you can see which provider actually won."""
    workers = STATE["workers"] or {}
    providers = {}
    for n, w in workers.items():
        res = getattr(w, "resolution", None)
        if res is not None:
            providers[n] = res.summary()
    return {"active": STATE["session"] is not None,
            "uid": STATE.get("uid"),
            "workers": {n: w.healthy() for n, w in workers.items()},
            "providers": providers}


def metrics_lines() -> list[str]:
    """Prometheus-style exposition from live worker metrics."""
    out = ["# Aura worker metrics"]
    for n, w in (STATE["workers"] or {}).items():
        m = w.metrics
        out += [f'aura_processed_total{{worker="{n}"}} {m.processed}',
                f'aura_errors_total{{worker="{n}"}} {m.errors}',
                f'aura_dropped_total{{worker="{n}"}} {m.dropped}',
                f'aura_restarts_total{{worker="{n}"}} {m.restarts}',
                f'aura_queue_depth{{worker="{n}"}} {m.queue_depth}',
                f'aura_healthy{{worker="{n}"}} {int(w.healthy())}']
    s = STATE["session"]
    if s is not None:
        out.append(f'aura_av_drift_ms {s.drift.current}')
    return out
