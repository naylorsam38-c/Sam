"""
Audio-input worker (spec §7 audio/VAD stage, Phase 4).

Owns the microphone ingress. For each incoming PCM frame it (a) forwards the
frame to the VAD worker and (b) appends it to a rolling buffer with a short
pre-roll. When the VAD declares end-of-speech, it slices the buffered utterance,
writes a 16 kHz mono wav, and hands it to STT — closing the mic → transcript loop.

Barge-in is handled upstream: VAD 'start' during SPEAKING triggers the session's
barge_in(); this worker just keeps capturing so the new utterance is transcribed.
"""
from __future__ import annotations

import collections
import os
import tempfile

import numpy as np
import soundfile as sf

from ..bus import Bus, Topic
from ..worker import BaseWorker, log


class AudioInputWorker(BaseWorker):
    name = "audio_in"

    def __init__(self, bus: Bus, vad, stt, sample_rate: int = 16000,
                 preroll_ms: int = 300, **kw):
        super().__init__(maxsize=128, item_timeout=1.0, on_full="drop_oldest", **kw)
        self.bus = bus
        self.vad = vad
        self.stt = stt
        self.sr = sample_rate
        self._buf: collections.deque = collections.deque(maxlen=2000)  # (idx,pcm)
        self._idx = 0
        self._speaking = False
        self._start_idx = 0
        self._preroll = int(preroll_ms / 1000 * sample_rate)
        bus.on(Topic.VAD, self._on_vad)

    async def handle(self, item: dict) -> None:
        pcm = item["pcm"]
        self._buf.append((self._idx, pcm))
        self._idx += len(np.frombuffer(pcm, dtype=np.int16))
        await self.vad.submit({"pcm": pcm, "ts": item.get("ts")})

    async def _on_vad(self, ev: dict) -> None:
        if ev["kind"] == "start":
            self._speaking = True
            self._start_idx = max(0, self._idx - self._preroll)
        elif ev["kind"] == "stop" and self._speaking:
            self._speaking = False
            wav = self._flush_utterance()
            if wav:
                await self.stt.submit({"wav_path": wav})

    def _flush_utterance(self) -> str | None:
        frames = [pcm for idx, pcm in self._buf if idx >= self._start_idx]
        if not frames:
            return None
        audio = np.concatenate([np.frombuffer(p, dtype=np.int16) for p in frames])
        if audio.size < self.sr * 0.2:      # ignore sub-200ms blips
            return None
        path = os.path.join(tempfile.gettempdir(),
                            f"aura_utt_{self._start_idx}.wav")
        sf.write(path, audio.astype(np.float32) / 32768.0, self.sr)
        log(self.name, "info", "utterance captured",
            samples=int(audio.size), path=path)
        return path
