"""Signaling route builds a pipeline and returns a valid WebRTC answer; health +
metrics endpoints report real worker state."""
import os

import pytest

pytest.importorskip("aiortc")
pytest.importorskip("httpx")
from aiortc import RTCPeerConnection, RTCSessionDescription  # noqa: E402
import httpx  # noqa: E402

os.environ["AURA_DEV"] = "1"                 # bypass token for the test
from aura.gateway.app import app            # noqa: E402
from aura.gateway import rtc                 # noqa: E402


async def test_offer_returns_answer_and_metrics():
    # a browser-like offerer with recv video/audio (+ mic) transceivers
    pc = RTCPeerConnection()
    pc.addTransceiver("video", direction="recvonly")
    pc.addTransceiver("audio", direction="sendrecv")
    pc.createDataChannel("aura")
    await pc.setLocalDescription(await pc.createOffer())

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as c:
        r = await c.post("/v1/rtc/offer",
                         json={"sdp": pc.localDescription.sdp,
                               "type": pc.localDescription.type})
        assert r.status_code == 200
        ans = r.json()
        assert ans["type"] == "answer" and "v=0" in ans["sdp"]
        # the answer is valid enough to apply on the offerer
        await pc.setRemoteDescription(RTCSessionDescription(ans["sdp"], ans["type"]))

        h = (await c.get("/healthz")).json()
        assert "workers" in h and h["workers"]        # real worker health present

        m = (await c.get("/metrics")).text
        assert "aura_healthy" in m and "aura_processed_total" in m

    await rtc._teardown()
    await pc.close()
