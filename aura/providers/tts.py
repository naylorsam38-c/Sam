"""
Text-to-speech providers.

  espeak    fallback    free, offline, robotic. The floor — always works.
  kokoro    selfhosted  Kokoro-82M, Apache-2.0 weights. The commercial default
                        on your own GPU: no per-minute fee, genuinely good.
  cartesia  api         Sonic. Lowest time-to-first-byte of the hosted options,
                        which is what you feel in a live conversation.
  elevenlabs api        Best raw voice quality; higher latency and price.

All four write a wav to the path they are given and return it, so the TTS worker
never learns which one ran.

NOTE ON API SHAPES: request/response formats for hosted services move. The calls
below match each vendor's documented API at time of writing; verify against
current docs before you rely on them in production. Both API providers fail
closed — a bad response raises, the registry falls through to the next engine.
"""
from __future__ import annotations

import asyncio
import os
import shutil
import subprocess

from .base import (Cost, ProviderInfo, ProviderUnavailable, Requires, Tier)
from .registry import register
from ..worker import log


# ── fallback: espeak-ng ─────────────────────────────────────────────────────
class EspeakTTS:
    info = ProviderInfo(
        name="espeak", tier=Tier.FALLBACK, licence="GPL-3.0-or-later",
        cost=Cost(note="free"),
        requires=Requires(binaries=("espeak-ng",)),
        quality=1, latency_ms=40, separate_process=True,
        note="Offline floor. GPL-3.0 is cleared here ONLY because espeak-ng is "
             "exec'd as its own binary and never linked — mere aggregation. "
             "Robotic; ship it as a fallback, never as the product voice.",
    )

    def __init__(self, **_: object) -> None: ...

    async def setup(self) -> None:
        if not shutil.which("espeak-ng"):
            raise ProviderUnavailable("espeak-ng not on PATH")

    async def synthesize(self, text: str, wav_path: str, *, voice: str,
                         sample_rate: int) -> str:
        await asyncio.to_thread(
            subprocess.run,
            ["espeak-ng", "-v", "en-us+f3", "-s", "155", "-w", wav_path, text],
            check=True, capture_output=True)
        return wav_path

    async def close(self) -> None: ...


# ── self-hosted: Kokoro-82M ─────────────────────────────────────────────────
class KokoroTTS:
    """Kokoro-82M. 82M params, runs comfortably on CPU and fast on any GPU.

    Apache-2.0 on both code and weights, which makes it the one open TTS you can
    ship commercially without reading a lawyer into the loop.
    """
    info = ProviderInfo(
        name="kokoro", tier=Tier.SELFHOSTED, licence="Apache-2.0",
        weight_licence="Apache-2.0",
        cost=Cost(gpu_hour=0.0, note="shares the render GPU; no marginal cost"),
        requires=Requires(packages=("kokoro",)),
        quality=4, latency_ms=150,
        note="Commercial default for self-hosted. Weights must be pre-downloaded "
             "and pinned on the build host (audit rule R3).",
    )

    def __init__(self, lang_code: str = "a", **_: object) -> None:
        self.lang_code = lang_code
        self._pipeline = None

    async def setup(self) -> None:
        try:
            from kokoro import KPipeline
        except Exception as e:
            raise ProviderUnavailable(f"kokoro not installed: {e!r}") from e
        try:
            self._pipeline = await asyncio.to_thread(KPipeline, lang_code=self.lang_code)
        except Exception as e:
            raise ProviderUnavailable(f"kokoro failed to load: {e!r}") from e
        log("tts.kokoro", "info", "loaded", lang=self.lang_code)

    async def synthesize(self, text: str, wav_path: str, *, voice: str,
                         sample_rate: int) -> str:
        if self._pipeline is None:
            raise ProviderUnavailable("kokoro not loaded")

        def _run() -> str:
            import numpy as np
            import soundfile as sf
            chunks = [audio for _, _, audio in
                      self._pipeline(text, voice=voice or "af_heart")]
            if not chunks:
                raise RuntimeError("kokoro produced no audio")
            wav = np.concatenate([np.asarray(c, dtype="float32") for c in chunks])
            sf.write(wav_path, wav, 24000)      # Kokoro is natively 24 kHz
            return wav_path

        return await asyncio.to_thread(_run)

    async def close(self) -> None:
        self._pipeline = None


# ── shared helper for the hosted providers ──────────────────────────────────
async def _post_bytes(url: str, *, headers: dict, json_body: dict,
                      timeout: float, provider: str) -> bytes:
    import httpx
    async with httpx.AsyncClient(timeout=timeout) as c:
        r = await c.post(url, headers=headers, json=json_body)
        if r.status_code >= 400:
            raise RuntimeError(f"{provider} HTTP {r.status_code}: {r.text[:200]}")
        return r.content


# ── API: Cartesia Sonic ─────────────────────────────────────────────────────
class CartesiaTTS:
    info = ProviderInfo(
        name="cartesia", tier=Tier.API, licence="Apache-2.0",
        weight_licence="commercial-use-allowed",
        cost=Cost(per_minute=0.02, note="approximate; verify current pricing"),
        requires=Requires(env=("CARTESIA_API_KEY",), packages=("httpx",)),
        quality=5, latency_ms=90,
        note="Lowest TTFB of the hosted options — the one that makes a live "
             "conversation feel unlaggy. Licence field records YOUR right to "
             "use the output commercially under their ToS, not their code.",
    )

    API = "https://api.cartesia.ai/tts/bytes"
    VERSION = "2024-06-10"

    def __init__(self, model: str = "sonic-2", **_: object) -> None:
        self.model = model

    async def setup(self) -> None:
        if not os.getenv("CARTESIA_API_KEY"):
            raise ProviderUnavailable("CARTESIA_API_KEY not set")

    async def synthesize(self, text: str, wav_path: str, *, voice: str,
                         sample_rate: int) -> str:
        body = {
            "model_id": self.model,
            "transcript": text,
            "voice": {"mode": "id", "id": voice},
            "output_format": {"container": "wav", "encoding": "pcm_s16le",
                              "sample_rate": sample_rate},
            "language": "en",
        }
        data = await _post_bytes(
            self.API, timeout=20.0, provider="cartesia", json_body=body,
            headers={"X-API-Key": os.environ["CARTESIA_API_KEY"],
                     "Cartesia-Version": self.VERSION,
                     "Content-Type": "application/json"})
        with open(wav_path, "wb") as f:
            f.write(data)
        return wav_path

    async def close(self) -> None: ...


# ── API: ElevenLabs ─────────────────────────────────────────────────────────
class ElevenLabsTTS:
    info = ProviderInfo(
        name="elevenlabs", tier=Tier.API, licence="Apache-2.0",
        weight_licence="commercial-use-allowed",
        cost=Cost(per_minute=0.10, note="approximate; character-billed, varies by plan"),
        requires=Requires(env=("ELEVENLABS_API_KEY",), packages=("httpx",)),
        quality=5, latency_ms=300,
        note="Best raw voice quality. Slower and pricier — good for pre-rendered "
             "content, less good for live turns. Commercial use requires a paid "
             "tier; the free tier does not grant it.",
    )

    API = "https://api.elevenlabs.io/v1/text-to-speech"

    def __init__(self, model: str = "eleven_flash_v2_5", **_: object) -> None:
        self.model = model

    async def setup(self) -> None:
        if not os.getenv("ELEVENLABS_API_KEY"):
            raise ProviderUnavailable("ELEVENLABS_API_KEY not set")

    async def synthesize(self, text: str, wav_path: str, *, voice: str,
                         sample_rate: int) -> str:
        import httpx
        url = f"{self.API}/{voice}?output_format=pcm_{sample_rate}"
        async with httpx.AsyncClient(timeout=30.0) as c:
            r = await c.post(url, headers={
                "xi-api-key": os.environ["ELEVENLABS_API_KEY"],
                "Content-Type": "application/json"},
                json={"text": text, "model_id": self.model})
            if r.status_code >= 400:
                raise RuntimeError(f"elevenlabs HTTP {r.status_code}: {r.text[:200]}")
            pcm = r.content
        # raw PCM back -> wrap as a wav so downstream stays format-agnostic
        import numpy as np
        import soundfile as sf
        audio = np.frombuffer(pcm, dtype=np.int16).astype("float32") / 32768.0
        await asyncio.to_thread(sf.write, wav_path, audio, sample_rate)
        return wav_path

    async def close(self) -> None: ...


register("tts", "espeak", EspeakTTS)
register("tts", "kokoro", KokoroTTS)
register("tts", "cartesia", CartesiaTTS)
register("tts", "elevenlabs", ElevenLabsTTS)
