"""
Speech-to-text providers.

  null            fallback    returns nothing, flags `uncertain`. Keeps the
                              pipeline alive on a box with no model and no key.
  faster-whisper  selfhosted  MIT code, MIT weights. The commercial default.
  deepgram        api         Nova-3. Fast and cheap per minute.

Every provider returns a `Transcript`, so the STT worker never branches on which
engine ran.
"""
from __future__ import annotations

import asyncio
import os

from .base import (Cost, ProviderInfo, ProviderUnavailable, Requires, Tier,
                   Transcript)
from .registry import register
from ..worker import log


# ── fallback: no model, no key ──────────────────────────────────────────────
class NullSTT:
    info = ProviderInfo(
        name="null", tier=Tier.FALLBACK, licence="MIT",
        cost=Cost(note="free"), quality=0, latency_ms=0,
        note="Transcribes nothing and says so. Exists so the session degrades "
             "to 'I didn't catch that' instead of crashing.",
    )

    def __init__(self, **_: object) -> None: ...

    async def setup(self) -> None: ...

    async def transcribe(self, wav_path: str) -> Transcript:
        return Transcript(text="", uncertain=True, no_speech=True)

    async def close(self) -> None: ...


# ── self-hosted: faster-whisper ─────────────────────────────────────────────
class FasterWhisperSTT:
    info = ProviderInfo(
        name="faster-whisper", tier=Tier.SELFHOSTED, licence="MIT",
        weight_licence="MIT",
        cost=Cost(gpu_hour=0.0, note="shares the render GPU; no marginal cost"),
        requires=Requires(packages=("faster_whisper",)),
        quality=4, latency_ms=250,
        note="Whisper weights are MIT — genuinely commercial-safe. Pre-download "
             "the CT2 weights and set local_files_only on the build host, or "
             "audit rule R3 fails the build for dynamic fetching.",
    )

    def __init__(self, model: str = "small.en", device: str = "auto",
                 compute_type: str = "int8", **_: object) -> None:
        self.model, self.device, self.compute_type = model, device, compute_type
        self._model = None

    async def setup(self) -> None:
        try:
            from faster_whisper import WhisperModel
        except Exception as e:
            raise ProviderUnavailable(f"faster-whisper not installed: {e!r}") from e
        try:
            self._model = await asyncio.to_thread(
                WhisperModel, self.model, device=self.device,
                compute_type=self.compute_type)
        except Exception as e:
            raise ProviderUnavailable(f"whisper weights unavailable: {e!r}") from e
        log("stt.whisper", "info", "loaded", model=self.model, device=self.device)

    async def transcribe(self, wav_path: str) -> Transcript:
        if self._model is None:
            raise ProviderUnavailable("whisper not loaded")

        def _run() -> Transcript:
            segments, _info = self._model.transcribe(wav_path, language="en")
            parts, low = [], False
            for seg in segments:
                parts.append(seg.text)
                if getattr(seg, "avg_logprob", 0.0) < -1.0:
                    low = True
            text = " ".join(parts).strip()
            return Transcript(text=text, uncertain=low or not text,
                              no_speech=not text, segments=parts)

        return await asyncio.to_thread(_run)

    async def close(self) -> None:
        self._model = None


# ── API: Deepgram ───────────────────────────────────────────────────────────
class DeepgramSTT:
    info = ProviderInfo(
        name="deepgram", tier=Tier.API, licence="Apache-2.0",
        weight_licence="commercial-use-allowed",
        cost=Cost(per_minute=0.0077, note="approximate; verify current pricing"),
        requires=Requires(env=("DEEPGRAM_API_KEY",), packages=("httpx",)),
        quality=5, latency_ms=120,
        note="Cheapest part of the hosted stack by a wide margin — STT is rarely "
             "where the money goes.",
    )

    API = "https://api.deepgram.com/v1/listen"

    def __init__(self, model: str = "nova-3", **_: object) -> None:
        self.model = model

    async def setup(self) -> None:
        if not os.getenv("DEEPGRAM_API_KEY"):
            raise ProviderUnavailable("DEEPGRAM_API_KEY not set")

    async def transcribe(self, wav_path: str) -> Transcript:
        import httpx
        with open(wav_path, "rb") as f:
            audio = f.read()
        params = {"model": self.model, "language": "en", "punctuate": "true",
                  "smart_format": "true"}
        async with httpx.AsyncClient(timeout=20.0) as c:
            r = await c.post(self.API, params=params, content=audio, headers={
                "Authorization": f"Token {os.environ['DEEPGRAM_API_KEY']}",
                "Content-Type": "audio/wav"})
            if r.status_code >= 400:
                raise RuntimeError(f"deepgram HTTP {r.status_code}: {r.text[:200]}")
            data = r.json()

        try:
            alt = data["results"]["channels"][0]["alternatives"][0]
        except (KeyError, IndexError):
            return Transcript(text="", uncertain=True, no_speech=True)
        text = (alt.get("transcript") or "").strip()
        conf = float(alt.get("confidence") or 0.0)
        return Transcript(text=text, uncertain=(not text) or conf < 0.6,
                          no_speech=not text)

    async def close(self) -> None: ...


register("stt", "null", NullSTT)
register("stt", "faster-whisper", FasterWhisperSTT)
register("stt", "deepgram", DeepgramSTT)
