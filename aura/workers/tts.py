"""
TTS worker. Turns a phrase into speech audio (spec §4 continuous buffer, §10
configurable engine).

The engine itself lives behind a provider (see `aura/providers/tts.py`), resolved
once at setup from the configured policy. This worker never learns whether it is
talking to Cartesia over HTTP or Kokoro on the local GPU — which is what lets you
flip between paying per minute and paying per GPU-hour with a config line.

Publishes TTS_AUDIO {session_id, turn_id, wav_path, pts, sample_rate}. Cancelled
mid-phrase on barge-in (BaseWorker.cancel_current) and drops queued phrases.
"""
from __future__ import annotations

import os
import tempfile
import uuid

from ..bus import Bus, Topic
from ..config import ProvidersCfg, TTSCfg
from ..providers import registry
from ..worker import BaseWorker, log


class TTSWorker(BaseWorker):
    name = "tts"

    def __init__(self, bus: Bus, cfg: TTSCfg,
                 providers: ProvidersCfg | None = None, **kw):
        super().__init__(maxsize=16, item_timeout=8.0, **kw)
        self.bus = bus
        self.cfg = cfg
        self.pcfg = providers or ProvidersCfg()
        self.provider = None
        self.resolution = None

    async def setup(self) -> None:
        self.provider, self.resolution = await registry.resolve(
            "tts", policy=self.pcfg.policy, engine=self.pcfg.tts_engine,
            commercial=self.pcfg.commercial)
        log(self.name, "info", "ready", engine=self.resolution.chosen,
            tier=self.resolution.info.tier)

    async def teardown(self) -> None:
        if self.provider is not None:
            await self.provider.close()

    async def handle(self, item: dict) -> None:
        if self.provider is None:
            raise RuntimeError("tts provider not resolved")
        text = item["text"]
        # uuid, not hash(): PYTHONHASHSEED randomisation made the old filename
        # scheme collide across turns and silently serve stale audio.
        wav = os.path.join(
            tempfile.gettempdir(),
            f"aura_{item['session_id']}_{item['turn_id']}_{uuid.uuid4().hex[:8]}.wav")
        await self.provider.synthesize(
            text, wav, voice=item.get("voice") or self.cfg.voice,
            sample_rate=self.cfg.sample_rate)
        await self.bus.publish(Topic.TTS_AUDIO, {
            "session_id": item["session_id"], "turn_id": item["turn_id"],
            "wav_path": wav, "sample_rate": self.cfg.sample_rate,
            "text": text,
            "emotion": item.get("emotion"), "intensity": item.get("intensity"),
            "gesture": item.get("gesture")})

    async def on_cancelled(self, item: dict) -> None:
        log(self.name, "info", "tts cancelled (barge-in)", turn=item.get("turn_id"))
