#!/usr/bin/env python3
"""
Phase 2 + 3 end-to-end demo — RUNS LOCALLY, no GPU, no mic, no paid services.

Proves the real pipeline: a streamed response from a (mock) Command Desk flows
through the actual Session + workers — phrase chunking → TTS → renderer → synced
audio+video capture — and is assembled into one talking clip. Also prints the
state timeline and per-turn timing the app would receive on the data channel.

    python scripts/e2e_demo.py
    -> samples/e2e_turn.mp4  (+ state/timeline printed)

Swap the mock for your real Command Desk by setting AURA_BRAIN_ENDPOINT; nothing
else changes (that is Phase 3).
"""
import asyncio
import os
import socket
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aura.config import Config
from aura.protocol import State
from aura.runtime import build_session
from aura.transport.base import CaptureTransport

PORT = 8791


def _wait_port(port, timeout=15):
    t0 = time.time()
    while time.time() - t0 < timeout:
        with socket.socket() as s:
            s.settimeout(0.3)
            try:
                s.connect(("127.0.0.1", port)); return True
            except OSError:
                time.sleep(0.2)
    return False


async def run():
    cfg = Config()
    cfg.brain.endpoint = f"http://127.0.0.1:{PORT}/chat"
    cfg.avatar.source_image = "assets/nova.png"
    fps = cfg.avatar.output_fps

    transport = CaptureTransport(fps=fps)
    session, workers = await build_session("demo", cfg, transport)
    workers["render"].disable_idle()   # capture only speaking frames for a clean clip

    # simulate the moment STT produced a final transcript for the user's turn
    print("USER: Is the report ready?")
    session.sm.to(State.THINKING)                      # IDLE -> THINKING (legal)
    await workers["brain"].submit({"session_id": "demo",
                                   "turn_id": "t1",
                                   "text": "Is the report ready?"})

    # wait until TTS has produced all phrases and frames have drained
    last_a, last_f, stable = -1, -1, 0
    for _ in range(200):
        await asyncio.sleep(0.1)
        a, f = len(transport.audio_segments), len(transport.frames)
        stable = stable + 1 if (a == last_a and f == last_f and a > 0) else 0
        last_a, last_f = a, f
        if stable >= 10:      # ~1s with no new audio or frames
            break

    for w in workers.values():
        await w.stop()

    os.makedirs("samples", exist_ok=True)
    out = transport.assemble("samples/e2e_turn.mp4")

    # report what the app's data channel received
    states = [e["data"].get("state") for e in transport.events if e["type"] == "state"]
    responses = [e["data"].get("text") for e in transport.events if e["type"] == "response_text"]
    print("STATE TIMELINE:", " -> ".join(states))
    print("RESPONSE TEXT :", " ".join(r for r in responses if r))
    print(f"AUDIO SEGMENTS: {len(transport.audio_segments)}  FRAMES: {len(transport.frames)}"
          f"  DRIFT samples: {len(session.drift.samples)}  peak drift(ms): "
          f"{max((abs(x) for x in session.drift.samples), default=0):.1f}")
    print("OUTPUT:", out)
    return out


def main():
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    mock = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "scripts.mock_commanddesk:app",
         "--port", str(PORT), "--log-level", "warning"], cwd=repo)
    try:
        if not _wait_port(PORT):
            print("mock Command Desk failed to start"); sys.exit(1)
        out = asyncio.run(run())
        sys.exit(0 if out else 2)
    finally:
        mock.terminate()
        try:
            mock.wait(timeout=5)
        except subprocess.TimeoutExpired:
            mock.kill()


if __name__ == "__main__":
    main()
