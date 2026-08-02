"""Phase 4 — live audio path through the REAL workers (synthetic mic frames).

No microphone needed: we push PCM frames into the audio-input worker exactly as
the transport would, and assert the VAD → capture → STT → brain loop fires, and
that speaking-time voice triggers a real barge-in that recovers to LISTENING.
"""
import asyncio

import numpy as np
import pytest

from aura.config import Config
from aura.protocol import Event, State
from aura.runtime import build_session
from aura.transport.base import CaptureTransport


def _frame(voiced: bool, n: int = 320) -> bytes:
    return np.full(n, 9000 if voiced else 0, dtype=np.int16).tobytes()


async def _feed(session, workers, voiced_frames: int, silence_frames: int):
    for _ in range(voiced_frames):
        await workers["audio_in"].submit({"pcm": _frame(True)})
        await asyncio.sleep(0.004)
    for _ in range(silence_frames):
        await workers["audio_in"].submit({"pcm": _frame(False)})
        await asyncio.sleep(0.004)
    await asyncio.sleep(0.2)


async def _build():
    cfg = Config()
    cfg.brain.endpoint = "http://127.0.0.1:9/chat"   # refuses fast (no hang)
    cfg.avatar.source_image = "assets/nova.png"
    transport = CaptureTransport()
    session, workers = await build_session("live", cfg, transport)
    return cfg, session, workers, transport


async def test_vad_capture_stt_loop():
    _, session, workers, transport = await _build()
    session.sm.to(State.LISTENING)                    # ready for the user
    await _feed(session, workers, voiced_frames=40, silence_frames=20)
    await asyncio.sleep(0.3)
    for w in workers.values():
        await w.stop()

    types = [e["type"] for e in transport.events]
    states = [e["data"].get("state") for e in transport.events if e["type"] == "state"]
    assert "final_transcript" in types                # STT emitted a final
    assert State.USER_SPEAKING.value in states        # VAD start moved state
    assert State.THINKING.value in states             # VAD stop moved state


async def test_barge_in_from_real_vad():
    _, session, workers, transport = await _build()
    # pretend the avatar is mid-answer
    session.sm.to(State.THINKING)
    session.sm.to(State.STARTING_SPEECH)
    session.sm.to(State.SPEAKING)
    session._speaking_turn = "prev"
    workers["tts"].q.put_nowait({"text": "still talking"})

    # user starts talking -> VAD start during SPEAKING -> barge_in()
    for _ in range(6):
        await workers["audio_in"].submit({"pcm": _frame(True)})
        await asyncio.sleep(0.01)
    await asyncio.sleep(0.3)
    for w in workers.values():
        await w.stop()

    types = [e["type"] for e in transport.events]
    assert "interrupted" in types                     # client was told
    assert session.sm.state in (State.LISTENING, State.USER_SPEAKING)
    assert workers["tts"].q.empty()                   # queued speech discarded
