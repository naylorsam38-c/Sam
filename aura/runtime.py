"""
Runtime assembler — wires the worker set + a Session + a Transport for ONE user
(spec §25: single reliable user before multi-user scaling). This is the process
`scripts/run_service.py` launches.

Data flow (spec target architecture):
  mic -> VAD -> STT -> [Command Desk] -> phrase stream -> TTS -> renderer ->
  publisher -> WebRTC -> app; state + transcript + timing events over data ch.
"""
from __future__ import annotations

import asyncio

from .bus import Bus, Topic
from .config import Config
from .metrics import DriftMeter
from .protocol import Envelope
from .render.quality import QualityController
from .session import Session
from .transport.base import NullTransport
from .workers import (AudioInputWorker, BrainConnector, PublisherWorker,
                      RendererWorker, STTWorker, TTSWorker, VADWorker)


async def build_session(session_id: str, cfg: Config, transport=None) -> tuple[Session, dict]:
    bus = Bus()
    drift = DriftMeter(cfg.drift_budget_ms)
    quality = QualityController(cfg.quality_default, cfg.drift_budget_ms)
    transport = transport or NullTransport()

    async def send(env: Envelope) -> None:
        await transport.send_event(env.json())

    # placeholder; replaced after Session exists (brain needs session.present)
    workers: dict = {}
    session = Session(session_id, cfg, bus, send, workers)

    workers["vad"] = VADWorker(bus)
    workers["stt"] = STTWorker(bus, cfg.stt, cfg.providers)
    workers["audio_in"] = AudioInputWorker(bus, workers["vad"], workers["stt"])
    workers["brain"] = BrainConnector(cfg.brain, session.present)
    workers["tts"] = TTSWorker(bus, cfg.tts, cfg.providers)
    workers["render"] = RendererWorker(bus, cfg.avatar, quality, cfg.providers)
    workers["publish"] = PublisherWorker(bus, transport, drift)

    # ── inter-worker wiring on the bus ──────────────────────────────────────
    # TTS audio drives the renderer (audio is the master clock); the publisher
    # already subscribes to TTS_AUDIO + RENDER_FRAME in its constructor.
    bus.on(Topic.TTS_AUDIO, workers["render"].submit)
    # Mic ingress -> audio-input worker: it forwards frames to VAD and, on
    # end-of-speech, captures the utterance wav and hands it to STT.
    transport.on_mic(lambda pcm: workers["audio_in"].submit({"pcm": pcm}))

    for w in workers.values():
        await w.start()
    return session, workers


async def run_forever(session_id: str = "primary") -> None:
    cfg = Config.load()
    session, workers = await build_session(session_id, cfg)
    try:
        while True:
            await asyncio.sleep(5)
            for name, w in workers.items():
                if not w.healthy():
                    from .worker import log
                    log("supervisor", "error", "worker unhealthy; restarting",
                        worker=name)
                    # stop() first: start() alone left the old task running and
                    # leaked another one on every supervisor pass.
                    try:
                        await w.stop()
                    except Exception as e:
                        log("supervisor", "warn", "stop during restart failed",
                            worker=name, error=repr(e))
                    w._stop.clear()
                    await w.start()
    finally:
        for w in workers.values():
            await w.stop()
