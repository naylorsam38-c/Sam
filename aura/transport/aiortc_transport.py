"""
Self-hosted WebRTC transport (aiortc) — no LiveKit server, no paid service.

Publishes the avatar as a real WebRTC video + audio track to a browser, receives
the user's microphone track, and carries events/controls on a data channel. This
is the fully self-contained streaming path used by the reference client and the
self-hosted run mode; it satisfies "all streaming runs on infrastructure you
control" with zero external dependencies.

Audio remains the master clock: video frames carry the audio-derived PTS set by
the renderer; the audio track streams the same TTS audio.
"""
from __future__ import annotations

import asyncio
import fractions
import json
from typing import Awaitable, Callable

import av
import numpy as np
import soundfile as sf
from aiortc import MediaStreamTrack, VideoStreamTrack

VIDEO_H, VIDEO_W = 620, 500
AUDIO_RATE = 48000
FRAME_SAMPLES = AUDIO_RATE // 50          # 20 ms


class _VideoTrack(VideoStreamTrack):
    """Streams frames pushed by the pipeline; repeats the last frame while idle
    so the track never stalls (the avatar is always visible)."""
    def __init__(self) -> None:
        super().__init__()
        self.q: asyncio.Queue = asyncio.Queue(maxsize=90)
        self._last = np.zeros((VIDEO_H, VIDEO_W, 3), np.uint8)

    async def recv(self):
        pts, time_base = await self.next_timestamp()
        try:
            self._last = self.q.get_nowait()
        except asyncio.QueueEmpty:
            pass
        vf = av.VideoFrame.from_ndarray(self._last, format="bgr24")
        vf.pts, vf.time_base = pts, time_base
        return vf


class _AudioTrack(MediaStreamTrack):
    kind = "audio"

    def __init__(self) -> None:
        super().__init__()
        self.q: asyncio.Queue = asyncio.Queue()
        self._buf = np.zeros(0, np.int16)
        self._pts = 0

    async def recv(self):
        await asyncio.sleep(FRAME_SAMPLES / AUDIO_RATE)      # pace at 20 ms
        while self._buf.size < FRAME_SAMPLES:
            try:
                self._buf = np.concatenate([self._buf, self.q.get_nowait()])
            except asyncio.QueueEmpty:
                pad = FRAME_SAMPLES - self._buf.size
                self._buf = np.concatenate([self._buf, np.zeros(pad, np.int16)])
        out, self._buf = self._buf[:FRAME_SAMPLES], self._buf[FRAME_SAMPLES:]
        frame = av.AudioFrame.from_ndarray(out.reshape(1, -1), format="s16", layout="mono")
        frame.sample_rate = AUDIO_RATE
        frame.pts, frame.time_base = self._pts, fractions.Fraction(1, AUDIO_RATE)
        self._pts += FRAME_SAMPLES
        return frame


class AiortcTransport:
    def __init__(self) -> None:
        self.video = _VideoTrack()
        self.audio = _AudioTrack()
        self._dc = None
        self._on_control: Callable[[dict], Awaitable[None]] | None = None
        self._on_mic: Callable[[bytes], Awaitable[None]] | None = None

    # ── pipeline -> client ──────────────────────────────────────────────────
    async def push_video(self, frame, pts: float) -> bool:
        if self.video.q.full():
            try:
                self.video.q.get_nowait()          # drop-oldest, freshest wins
            except asyncio.QueueEmpty:
                pass
        self.video.q.put_nowait(frame)
        return True

    async def push_audio(self, wav_path: str, sample_rate: int) -> bool:
        data, sr = sf.read(wav_path)
        if getattr(data, "ndim", 1) > 1:
            data = data.mean(axis=1)
        if sr != AUDIO_RATE and len(data):
            n = int(len(data) * AUDIO_RATE / sr)
            data = np.interp(np.linspace(0, len(data), n, endpoint=False),
                             np.arange(len(data)), data)
        pcm = (np.clip(data, -1, 1) * 32767).astype(np.int16)
        await self.audio.q.put(pcm)
        return True

    async def send_event(self, envelope: dict) -> None:
        if self._dc and self._dc.readyState == "open":
            self._dc.send(json.dumps(envelope))

    def on_control(self, handler): self._on_control = handler
    def on_mic(self, handler): self._on_mic = handler

    # ── attach to a peer connection (called by signaling) ───────────────────
    def attach(self, pc, create_data_channel: bool = False) -> None:
        pc.addTrack(self.video)
        pc.addTrack(self.audio)

        def _wire_dc(dc):
            self._dc = dc

            @dc.on("message")
            def _msg(msg):
                if self._on_control:
                    try:
                        asyncio.ensure_future(self._on_control(json.loads(msg)))
                    except Exception:
                        pass

        if create_data_channel:                    # offerer side (e.g. tests)
            _wire_dc(pc.createDataChannel("aura"))
        else:                                       # answerer side: browser opens it
            @pc.on("datachannel")
            def _on_dc(channel):
                _wire_dc(channel)

        @pc.on("track")
        def _track(track):
            if track.kind == "audio" and self._on_mic:
                asyncio.ensure_future(self._read_mic(track))

    async def _read_mic(self, track) -> None:
        """Decode the browser mic track to 16 kHz mono PCM and feed on_mic."""
        resampler = av.AudioResampler(format="s16", layout="mono", rate=16000)
        try:
            while True:
                frame = await track.recv()
                for r in resampler.resample(frame):
                    pcm = bytes(r.planes[0])[: r.samples * 2]
                    await self._on_mic(pcm)
        except Exception:
            return

    async def start(self, room: str, identity: str) -> None: ...
    async def close(self) -> None: ...
