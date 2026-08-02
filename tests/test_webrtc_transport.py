"""The self-hosted aiortc transport must stream a real avatar frame over a real
WebRTC offer/answer (no LiveKit, no paid service)."""
import asyncio

import numpy as np
import pytest

aiortc = pytest.importorskip("aiortc")
from aiortc import RTCPeerConnection  # noqa: E402

from aura.transport.aiortc_transport import AiortcTransport  # noqa: E402


async def test_frame_streams_over_webrtc():
    tp = AiortcTransport()
    sender, receiver = RTCPeerConnection(), RTCPeerConnection()
    tp.attach(sender, create_data_channel=True)      # transport is the offerer here

    got = asyncio.Event()
    dims = {}

    @receiver.on("track")
    def _on_track(track):
        if track.kind == "video":
            async def pull():
                fr = await track.recv()
                dims["w"], dims["h"] = fr.width, fr.height
                got.set()
            asyncio.ensure_future(pull())

    await tp.push_video(np.full((620, 500, 3), 90, np.uint8), 0.0)
    await sender.setLocalDescription(await sender.createOffer())
    await receiver.setRemoteDescription(sender.localDescription)
    await receiver.setLocalDescription(await receiver.createAnswer())
    await sender.setRemoteDescription(receiver.localDescription)

    await asyncio.wait_for(got.wait(), 10)
    await sender.close(); await receiver.close()
    assert (dims["w"], dims["h"]) == (500, 620)      # avatar frame really arrived
