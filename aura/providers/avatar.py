"""
Avatar (lip-sync render) providers.

  fallback  fallback    the CPU warp renderer. Never freezes, never photoreal.
  musetalk  selfhosted  MuseTalk v1.5 on your own GPU. MIT code, weights granted
                        for commercial use. This is the commercial-grade path
                        you own outright.
  simli     api         hosted real-time face. Best quality-per-effort, bills
                        per minute, and plugs in at a different layer — see below.

DRIVING VIDEO — the thing that separates a demo from a product
--------------------------------------------------------------
MuseTalk (like every hosted avatar service) inpaints the mouth region over an
existing frame sequence. Give it ONE still image and every frame shares the same
head pose, so the result reads as a photo with a moving mouth. Give it a short
loop of real footage — a person sitting still, blinking, breathing, shifting
slightly — and it reads as a person.

So `driving_video` is not optional polish. It is the single highest-leverage
input to perceived quality, and it costs one 20-second clip. `aura/studio/`
generates one if you do not have footage of the subject.
"""
from __future__ import annotations

import asyncio
import os
from typing import Iterator

import numpy as np

from .base import (Cost, ProviderInfo, ProviderUnavailable, Requires, Tier)
from .registry import register
from ..worker import log


# ── fallback: the CPU warp renderer ─────────────────────────────────────────
class FallbackAvatar:
    info = ProviderInfo(
        name="fallback", tier=Tier.FALLBACK, licence="MIT",
        cost=Cost(note="free"), quality=1, latency_ms=20,
        note="Amplitude-driven mouth warp — NOT viseme lip-sync. Its job is to "
             "never freeze and to prove the audio-mastered clock end to end. "
             "Do not ship it as the product.",
    )

    def __init__(self, source_image: str = "assets/nova.png", fps: int = 25,
                 **_: object) -> None:
        self.source_image, self.fps = source_image, fps
        self._r = None

    async def setup(self) -> None:
        from ..render.fallback import FallbackRenderer
        try:
            self._r = FallbackRenderer(self.source_image, fps=self.fps)
        except Exception as e:
            raise ProviderUnavailable(f"source image unusable: {e!r}") from e
        self._r.warmup()

    def idle_frame(self, state: str, t: float) -> np.ndarray:
        return self._r.idle_frame(state, t)

    def speaking_frames(self, wav_path: str) -> Iterator[tuple[np.ndarray, float]]:
        return self._r.speaking_frames(wav_path)

    async def close(self) -> None:
        self._r = None


# ── self-hosted: MuseTalk ───────────────────────────────────────────────────
class MuseTalkAvatar:
    """Real-time mouth inpainting on a driving frame sequence.

    Requires a MuseTalk checkout with downloaded weights, pointed at by
    AURA_MUSETALK_HOME. It is deliberately strict about readiness: `setup()`
    runs one real forward pass and only then reports itself usable. A renderer
    that claims availability and then raises mid-turn produces a frozen face —
    the exact failure this codebase was bitten by before.
    """
    info = ProviderInfo(
        name="musetalk", tier=Tier.SELFHOSTED, licence="MIT",
        weight_licence="commercial-use-allowed",
        cost=Cost(gpu_hour=0.50,
                  note="one 4090/L40S-class GPU, rented. Serves 1-3 concurrent "
                       "sessions; owning the card removes this entirely."),
        requires=Requires(env=("AURA_MUSETALK_HOME",), packages=("torch",), gpu=True),
        quality=4, latency_ms=400,
        note="MuseTalk's own code is MIT and its weights are granted for "
             "commercial use, BUT its bundled deps must be audited separately "
             "and its supplied TEST DATA is non-commercial and must not ship.",
    )

    def __init__(self, source_image: str = "assets/nova.png",
                 driving_video: str | None = None, fps: int = 25,
                 device: str = "cuda:0", **_: object) -> None:
        self.source_image = source_image
        self.driving_video = driving_video or os.getenv("AURA_DRIVING_VIDEO")
        self.fps, self.device = fps, device
        self._model = None
        self._frames: list[np.ndarray] = []

    async def setup(self) -> None:
        home = os.getenv("AURA_MUSETALK_HOME")
        if not home or not os.path.isdir(home):
            raise ProviderUnavailable(f"AURA_MUSETALK_HOME not a directory: {home!r}")

        def _load():
            import sys
            if home not in sys.path:
                sys.path.insert(0, home)
            # MuseTalk exposes its loader differently across releases; try the
            # documented entry point and fail loudly rather than guessing.
            from musetalk.utils.utils import load_all_model  # type: ignore
            return load_all_model()

        try:
            self._model = await asyncio.to_thread(_load)
        except Exception as e:
            raise ProviderUnavailable(f"MuseTalk load failed: {e!r}") from e

        self._frames = await asyncio.to_thread(self._load_driving_frames)
        if not self._frames:
            raise ProviderUnavailable("no driving frames (bad image and video)")

        # Prove it can actually infer before claiming availability.
        try:
            await asyncio.to_thread(self._dummy_forward)
        except Exception as e:
            raise ProviderUnavailable(f"MuseTalk dummy forward failed: {e!r}") from e

        log("avatar.musetalk", "info", "ready", device=self.device,
            driving_frames=len(self._frames),
            source="video" if self.driving_video else "still-image",
            warning=None if self.driving_video else
            "single still image — expect photo-with-moving-mouth quality")

    def _load_driving_frames(self) -> list[np.ndarray]:
        """Driving video if we have one, else the still repeated. A still gives
        a fixed head pose; that ceiling is the reason to record a loop."""
        import cv2
        if self.driving_video and os.path.exists(self.driving_video):
            cap = cv2.VideoCapture(self.driving_video)
            frames = []
            while True:
                ok, f = cap.read()
                if not ok:
                    break
                frames.append(f)
            cap.release()
            if frames:
                return frames + frames[::-1]     # ping-pong so the loop seams
        img = cv2.imread(self.source_image)
        return [img] if img is not None else []

    def _dummy_forward(self) -> None:
        raise NotImplementedError(
            "wire MuseTalk's inference call here on the GPU host — see "
            "docs/GPU_HOST_SETUP.md. Until then this provider correctly reports "
            "unavailable and the registry falls through.")

    def idle_frame(self, state: str, t: float) -> np.ndarray:
        idx = int(t * self.fps) % max(1, len(self._frames))
        return self._frames[idx]

    def speaking_frames(self, wav_path: str) -> Iterator[tuple[np.ndarray, float]]:
        if self._model is None:
            raise ProviderUnavailable("MuseTalk not loaded")
        raise NotImplementedError("enable on the GPU host with MuseTalk weights")

    async def close(self) -> None:
        self._model = None
        self._frames = []


# ── API: Simli ──────────────────────────────────────────────────────────────
class SimliAvatar:
    """Hosted real-time face, billed per minute.

    ARCHITECTURAL NOTE — this one does not fit `speaking_frames` cleanly, and
    pretending otherwise would cost you latency. Simli returns video over its
    own WebRTC connection. There are two ways to wire it:

      client-direct (recommended) — the browser opens a second peer connection
        straight to Simli using the session token from `start_session()`. One
        network hop, lowest latency, and the frames never touch your server.
        Aura keeps the state machine, barge-in and transcript channel.

      server-relay — your server ingests Simli's WebRTC video, decodes it and
        re-publishes through Aura's own transport. Uniform, but adds a decode +
        re-encode hop and 100ms+ of latency for no quality gain.

    `start_session()` implements the client-direct path. `speaking_frames`
    deliberately raises rather than shipping a slow relay you did not ask for.
    """
    info = ProviderInfo(
        name="simli", tier=Tier.API, licence="Apache-2.0",
        weight_licence="commercial-use-allowed",
        cost=Cost(per_minute=0.03, note="approximate; verify current pricing"),
        requires=Requires(env=("SIMLI_API_KEY", "SIMLI_FACE_ID"),
                          packages=("httpx",)),
        quality=5, latency_ms=200,
        note="Fastest route to commercial quality with zero capex. You are "
             "renting the face — check their ToS covers your use, and keep the "
             "self-hosted path warm so you are never locked in.",
    )

    API = "https://api.simli.ai/startAudioToVideoSession"

    def __init__(self, **_: object) -> None:
        self.session_token: str | None = None

    async def setup(self) -> None:
        for k in ("SIMLI_API_KEY", "SIMLI_FACE_ID"):
            if not os.getenv(k):
                raise ProviderUnavailable(f"{k} not set")

    async def start_session(self) -> dict:
        """Create a Simli session and return the token the browser connects with."""
        import httpx
        body = {"apiKey": os.environ["SIMLI_API_KEY"],
                "faceId": os.environ["SIMLI_FACE_ID"],
                "handleSilence": True, "maxSessionLength": 3600,
                "maxIdleTime": 300}
        async with httpx.AsyncClient(timeout=15.0) as c:
            r = await c.post(self.API, json=body)
            if r.status_code >= 400:
                raise RuntimeError(f"simli HTTP {r.status_code}: {r.text[:200]}")
            data = r.json()
        self.session_token = data.get("session_token")
        if not self.session_token:
            raise RuntimeError(f"simli returned no session_token: {data}")
        return data

    def idle_frame(self, state: str, t: float) -> np.ndarray:
        raise NotImplementedError("Simli renders its own idle motion server-side")

    def speaking_frames(self, wav_path: str) -> Iterator[tuple[np.ndarray, float]]:
        raise NotImplementedError(
            "Simli streams video client-direct; use start_session() and connect "
            "the browser. See the architectural note in this class.")

    async def close(self) -> None:
        self.session_token = None


register("avatar", "fallback", FallbackAvatar)
register("avatar", "musetalk", MuseTalkAvatar)
register("avatar", "simli", SimliAvatar)
