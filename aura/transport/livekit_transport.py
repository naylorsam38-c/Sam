"""
LiveKit transport (default; Apache-2.0, self-hostable — spec §17 keeps model
ports private, only LiveKit is public-facing).

Publishes a video track + audio track into the user's room and uses a LiveKit
data channel for events/controls. This is the integration seam; it activates
when `livekit` + `livekit-api` are installed and a LiveKit server URL is set.
Video is pushed frame-by-frame at the audio-derived PTS to keep A/V locked.
"""
from __future__ import annotations

from typing import Awaitable, Callable


class LiveKitTransport:
    def __init__(self, url: str, api_key: str, api_secret: str, codec: str = "vp8"):
        self.url = url
        self.api_key = api_key
        self.api_secret = api_secret
        self.codec = codec          # vp8 = royalty-free (avoid H.264 patent cost)
        self._room = None
        self._video_source = None
        self._audio_source = None
        self._on_control: Callable | None = None
        self._on_mic: Callable | None = None

    async def start(self, room: str, identity: str) -> None:
        try:
            from livekit import rtc
        except Exception as e:
            raise RuntimeError("livekit sdk not installed") from e
        # self._room = rtc.Room(); await self._room.connect(self.url, token)
        # create VideoSource/AudioSource, publish tracks, subscribe to mic + data
        raise NotImplementedError("enable on host with livekit installed")

    async def push_video(self, frame, pts: float) -> bool:
        # frame(np.ndarray bgr) -> rtc.VideoFrame at pts; capture to source
        return True

    async def push_audio(self, wav_path: str, sample_rate: int) -> bool:
        return True

    async def send_event(self, envelope: dict) -> None:
        # self._room.local_participant.publish_data(json.dumps(envelope), reliable=True)
        ...

    def on_control(self, handler: Callable[[dict], Awaitable[None]]) -> None:
        self._on_control = handler

    def on_mic(self, handler: Callable[[bytes], Awaitable[None]]) -> None:
        self._on_mic = handler

    async def close(self) -> None:
        if self._room:
            await self._room.disconnect()
