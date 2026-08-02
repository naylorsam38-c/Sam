"""TTS audio must actually drive rendered frames, and MuseTalk-unavailable must
fall back to CPU (never a frozen face)."""
import asyncio
import os
import shutil
import subprocess
import tempfile

import pytest

from aura.bus import Bus, Topic
from aura.config import AvatarCfg
from aura.render.quality import QualityController
from aura.workers.renderer import RendererWorker

pytestmark = pytest.mark.skipif(
    not shutil.which("espeak-ng"), reason="espeak-ng not installed")


async def test_tts_audio_drives_frames():
    wav = os.path.join(tempfile.gettempdir(), "aura_wiretest.wav")
    subprocess.run(["espeak-ng", "-w", wav, "hello there this is a test"],
                   check=True, capture_output=True)

    bus = Bus()
    frames = []
    bus.on(Topic.RENDER_FRAME, lambda ev: frames.append(ev) or asyncio.sleep(0))

    w = RendererWorker(bus, AvatarCfg(source_image="assets/nova.png"),
                       QualityController())
    await w.start()
    # No GPU and no API keys here, so the registry must land on the CPU
    # fallback rather than a provider that would raise mid-turn.
    assert w.resolution.chosen == "fallback"
    assert w.resolution.info.tier == "fallback"
    # ...and it must say why each better provider was skipped, so an operator
    # can tell "no GPU" apart from "wrong config".
    assert any("musetalk" == name for name, _ in w.resolution.skipped)
    await w.submit({"wav_path": wav, "sample_rate": 22050,
                    "session_id": "s", "turn_id": "t"})
    for _ in range(50):
        await asyncio.sleep(0.05)
        if frames:
            break
    await w.stop()
    assert len(frames) > 0                       # audio produced video frames
    assert frames[0]["audio_pts"] == frames[0]["video_pts"]   # audio-mastered
