"""
Speech-recognition worker (spec §10 configurable).

The engine lives behind a provider (`aura/providers/stt.py`), resolved once at
setup from the configured policy — faster-whisper on your own box, Deepgram over
HTTP, or a null provider that keeps the session alive when neither is present.

Handles uncertain transcription (spec §20): if confidence is low or the result is
empty, it emits an 'uncertain'/'no_speech' final so the session can re-prompt
instead of sending junk to Command Desk.
"""
from __future__ import annotations

from ..bus import Bus, Topic
from ..config import ProvidersCfg, STTCfg
from ..providers import registry
from ..worker import BaseWorker, log


class STTWorker(BaseWorker):
    name = "stt"

    def __init__(self, bus: Bus, cfg: STTCfg,
                 providers: ProvidersCfg | None = None, **kw):
        super().__init__(maxsize=8, item_timeout=10.0, **kw)
        self.bus = bus
        self.cfg = cfg
        self.pcfg = providers or ProvidersCfg()
        self.provider = None
        self.resolution = None

    async def setup(self) -> None:
        self.provider, self.resolution = await registry.resolve(
            "stt", policy=self.pcfg.policy, engine=self.pcfg.stt_engine,
            commercial=self.pcfg.commercial,
            model=self.cfg.model, device=self.cfg.device,
            compute_type=self.cfg.compute_type)
        log(self.name, "info", "ready", engine=self.resolution.chosen,
            tier=self.resolution.info.tier)

    async def teardown(self) -> None:
        if self.provider is not None:
            await self.provider.close()

    async def handle(self, item: dict) -> None:
        if self.provider is None:
            raise RuntimeError("stt provider not resolved")
        tx = await self.provider.transcribe(item["wav_path"])
        for seg in tx.segments:
            await self.bus.publish(Topic.TRANSCRIPT_PARTIAL, {"text": seg})
        await self.bus.publish(Topic.TRANSCRIPT_FINAL, {
            "text": tx.text, "uncertain": tx.uncertain, "no_speech": tx.no_speech})
