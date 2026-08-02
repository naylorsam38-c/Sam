"""
Voice-activity worker (spec §4, §3 immediate barge-in detection).

Consumes raw mic frames (16 kHz mono PCM) and emits VAD start/stop on the bus.
Default engine Silero VAD (MIT, commercial-ok); energy-gate fallback so it runs
without the model. On speech start it triggers barge-in upstream via the session
(the session subscribes to Topic.VAD).
"""
from __future__ import annotations

import numpy as np

from ..bus import Bus, Topic
from ..worker import BaseWorker, log


class VADWorker(BaseWorker):
    name = "vad"

    def __init__(self, bus: Bus, engine: str = "silero", sample_rate: int = 16000, **kw):
        super().__init__(maxsize=64, item_timeout=1.0, on_full="drop_oldest", **kw)
        self.bus = bus
        self.engine = engine
        self.sr = sample_rate
        self._speaking = False
        self._silence = 0
        self._model = None

    async def setup(self) -> None:
        if self.engine == "silero":
            try:
                # import torch; self._model, _ = torch.hub.load('snakers4/silero-vad', 'silero_vad')
                self._model = None    # integration point
            except Exception:
                self._model = None
        log(self.name, "info", "ready",
            engine="silero" if self._model else "energy-gate")

    async def handle(self, item: dict) -> None:
        pcm = np.frombuffer(item["pcm"], dtype=np.int16).astype(np.float32) / 32768.0
        voiced = self._is_voiced(pcm)
        if voiced and not self._speaking:
            self._speaking, self._silence = True, 0
            await self.bus.publish(Topic.VAD, {"kind": "start", "ts": item.get("ts")})
        elif not voiced and self._speaking:
            self._silence += 1
            if self._silence > 12:      # ~ hangover before declaring stop
                self._speaking = False
                await self.bus.publish(Topic.VAD, {"kind": "stop", "ts": item.get("ts")})

    def _is_voiced(self, pcm: np.ndarray) -> bool:
        if self._model is not None:
            # return self._model(torch.from_numpy(pcm), self.sr).item() > 0.5
            pass
        rms = float(np.sqrt(np.mean(pcm ** 2) + 1e-9))
        return rms > 0.02
