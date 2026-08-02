"""
Transport interface (spec §10). A transport publishes audio+video and carries
the bidirectional data channel (events out, controls in).
"""
from __future__ import annotations

from typing import Awaitable, Callable, Protocol


class Transport(Protocol):
    async def start(self, room: str, identity: str) -> None: ...
    async def push_audio(self, wav_path: str, sample_rate: int) -> bool: ...
    async def push_video(self, frame, pts: float) -> bool: ...
    async def send_event(self, envelope: dict) -> None: ...
    def on_control(self, handler: Callable[[dict], Awaitable[None]]) -> None: ...
    def on_mic(self, handler: Callable[[bytes], Awaitable[None]]) -> None: ...
    async def close(self) -> None: ...


class NullTransport:
    """Headless sink for tests: counts frames, drops everything else."""
    def __init__(self) -> None:
        self.audio = 0
        self.video = 0

    async def start(self, room: str, identity: str) -> None: ...
    async def push_audio(self, wav_path: str, sample_rate: int) -> bool:
        self.audio += 1; return True
    async def push_video(self, frame, pts: float) -> bool:
        self.video += 1; return True
    async def send_event(self, envelope: dict) -> None: ...
    def on_control(self, handler) -> None: ...
    def on_mic(self, handler) -> None: ...
    async def close(self) -> None: ...


class CaptureTransport:
    """Records the synchronised audio + video + data-channel events a real
    client would receive, and can assemble them into one talking-clip mp4.
    Used by the local e2e demo (no LiveKit/GPU needed) to prove the pipeline."""
    def __init__(self, fps: int = 25) -> None:
        self.fps = fps
        self.audio_segments: list[tuple[str, int]] = []
        self.frames: list = []          # list[np.ndarray]
        self.events: list[dict] = []

    async def start(self, room: str, identity: str) -> None: ...

    async def push_audio(self, wav_path: str, sample_rate: int) -> bool:
        self.audio_segments.append((wav_path, sample_rate)); return True

    async def push_video(self, frame, pts: float) -> bool:
        self.frames.append(frame); return True

    async def send_event(self, envelope: dict) -> None:
        self.events.append(envelope)

    def on_control(self, handler) -> None: ...
    def on_mic(self, handler) -> None: ...
    async def close(self) -> None: ...

    def assemble(self, out_mp4: str) -> str | None:
        """Concatenate captured audio + frames into one synced mp4."""
        import subprocess
        import cv2
        import numpy as np
        import soundfile as sf
        if not self.frames or not self.audio_segments:
            return None
        # concat audio (all segments share the TTS sample rate)
        chunks, sr = [], self.audio_segments[0][1]
        for path, _ in self.audio_segments:
            a, s = sf.read(path)
            if a.ndim > 1:
                a = a.mean(axis=1)
            chunks.append(a)
        wav = np.concatenate(chunks) if chunks else np.zeros(1)
        sf.write(out_mp4.replace(".mp4", ".wav"), wav, sr)
        # write frames
        H, W = self.frames[0].shape[:2]
        vpath = out_mp4.replace(".mp4", "_v.mp4")
        vw = cv2.VideoWriter(vpath, cv2.VideoWriter_fourcc(*"mp4v"), self.fps, (W, H))
        for f in self.frames:
            vw.write(f)
        vw.release()
        subprocess.run(["ffmpeg", "-y", "-i", vpath, "-i", out_mp4.replace(".mp4", ".wav"),
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
                        "-shortest", out_mp4], check=True, capture_output=True)
        return out_mp4
