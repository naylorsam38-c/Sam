"""
WebRTC publishing worker (spec §5, §6). Publishes synchronised audio + video to
the client. Audio is the master clock; each video frame carries the audio PTS it
was rendered against, and the publisher measures real drift continuously.

Transport is pluggable (spec §10): default LiveKit (Apache-2.0). A local aiortc
transport is provided for the reference browser client without a LiveKit server.
No-op sink is used in headless tests.
"""
from __future__ import annotations

from ..bus import Bus, Topic
from ..metrics import DriftMeter
from ..worker import BaseWorker, log


class PublisherWorker(BaseWorker):
    name = "publish"

    def __init__(self, bus: Bus, transport, drift: DriftMeter, **kw):
        super().__init__(maxsize=8, item_timeout=2.0, on_full="drop_oldest", **kw)
        self.bus = bus
        self.transport = transport      # object with push_video(frame,pts) / push_audio
        self.drift = drift
        self.published = 0
        bus.on(Topic.RENDER_FRAME, self._on_frame)
        bus.on(Topic.TTS_AUDIO, self._on_audio)

    async def _on_audio(self, ev: dict) -> None:
        if self.transport:
            await self.transport.push_audio(ev["wav_path"], ev["sample_rate"])

    async def _on_frame(self, ev: dict) -> None:
        d = self.drift.sample(ev["audio_pts"], ev["video_pts"])
        if self.transport:
            ok = await self.transport.push_video(ev["frame"], ev["video_pts"])
            if not ok:
                self.metrics.dropped += 1
        self.published += 1
        if self.drift.over_budget:
            log(self.name, "warn", "av drift over budget", drift_ms=d)

    async def handle(self, item) -> None:  # unused: this worker is event-driven
        pass
