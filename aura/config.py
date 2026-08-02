"""
Configuration loader. Everything model-related is config, never hardcoded
(spec §10). Reads config/aura.yaml, overlaid by env vars (AURA_*).
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

import yaml


@dataclass
class STTCfg:
    engine: str = "faster-whisper"
    model: str = "small.en"
    device: str = "cuda"
    compute_type: str = "int8_float16"


@dataclass
class TTSCfg:
    engine: str = "kokoro"      # Apache-2.0, commercial-safe (see LICENSING)
    voice: str = "nova"
    sample_rate: int = 24000


@dataclass
class AvatarCfg:
    lipsync: str = "musetalk"   # MIT code; weights commercial-ok; AUDIT bundled deps + drop test data
    motion: str = "liveportrait"  # MIT code; MUST swap InsightFace detector
    enhancer: str = "gfpgan"    # NOT codeformer (non-commercial)
    output_width: int = 720
    output_height: int = 1280
    output_fps: int = 25
    source_image: str = "assets/nova.png"
    # Short loop of real footage the lip-sync model inpaints onto. This is the
    # single biggest lever on perceived quality — a still image gives one fixed
    # head pose for every frame. Generate one with `scripts/make_avatar.py`.
    driving_video: str | None = None


@dataclass
class BrainCfg:
    mode: str = "external"      # never rebuild the brain
    endpoint: str = "http://commanddesk-internal/chat"
    timeout_s: float = 30.0


@dataclass
class TransportCfg:
    engine: str = "livekit"     # Apache-2.0
    codec: str = "vp8"          # royalty-free default; h264 has patent cost
    data_channel: bool = True
    url: str = "ws://localhost:7880"


@dataclass
class GPUCfg:
    stt_mem_mb: int = 1500
    tts_mem_mb: int = 1500
    render_mem_mb: int = 6000
    warmup: bool = True
    # move a stage to another device later without code changes:
    devices: dict[str, str] = field(default_factory=lambda: {
        "stt": "cuda:0", "tts": "cuda:0", "render": "cuda:0"})


@dataclass
class ProvidersCfg:
    """The API-vs-self-hosted switch.

    `policy` picks the preference order (see providers/registry.POLICIES):
      api        best hosted quality, bills per minute, no capex
      selfhosted open weights on your GPU, bills per GPU-hour, no per-minute fee
      auto       prefer local, borrow the API only when local cannot run
      offline    never leaves the machine, never bills

    Per-kind `engine` pins one specific provider; "auto" follows the policy.
    The chain always ends in a dependency-free fallback, so a missing key or a
    missing GPU degrades instead of failing.
    """
    policy: str = "auto"
    tts_engine: str = "auto"
    stt_engine: str = "auto"
    avatar_engine: str = "auto"
    commercial: bool = True        # refuse non-commercially-licensed providers
    utilisation: float = 1.0       # expected GPU busy fraction, for cost maths


@dataclass
class StudioCfg:
    """Avatar asset generation (aura/studio) — the picture and driving video."""
    image_engine: str = "flux-schnell"   # Apache-2.0; NOT flux-dev (non-commercial)
    video_engine: str = "wan"            # Wan 2.2, Apache-2.0
    out_dir: str = "assets/generated"
    driving_seconds: float = 8.0
    seed: int = 0


@dataclass
class Config:
    stt: STTCfg = field(default_factory=STTCfg)
    tts: TTSCfg = field(default_factory=TTSCfg)
    avatar: AvatarCfg = field(default_factory=AvatarCfg)
    brain: BrainCfg = field(default_factory=BrainCfg)
    transport: TransportCfg = field(default_factory=TransportCfg)
    gpu: GPUCfg = field(default_factory=GPUCfg)
    providers: ProvidersCfg = field(default_factory=ProvidersCfg)
    studio: StudioCfg = field(default_factory=StudioCfg)
    quality_default: int = 3
    drift_budget_ms: int = 80

    @staticmethod
    def load(path: str = "config/aura.yaml") -> "Config":
        raw: dict[str, Any] = {}
        if os.path.exists(path):
            with open(path) as f:
                raw = yaml.safe_load(f) or {}
        def sub(cls, key):
            return cls(**{k: v for k, v in (raw.get(key) or {}).items()
                          if k in cls.__annotations__})
        cfg = Config(
            stt=sub(STTCfg, "stt"), tts=sub(TTSCfg, "tts"),
            avatar=sub(AvatarCfg, "avatar"), brain=sub(BrainCfg, "brain"),
            transport=sub(TransportCfg, "transport"), gpu=sub(GPUCfg, "gpu"),
            providers=sub(ProvidersCfg, "providers"), studio=sub(StudioCfg, "studio"),
        )
        if "quality_default" in raw:
            cfg.quality_default = int(raw["quality_default"])
        if "drift_budget_ms" in raw:
            cfg.drift_budget_ms = int(raw["drift_budget_ms"])
        # env overrides
        if os.getenv("AURA_BRAIN_ENDPOINT"):
            cfg.brain.endpoint = os.environ["AURA_BRAIN_ENDPOINT"]
        if os.getenv("AURA_TRANSPORT_URL"):
            cfg.transport.url = os.environ["AURA_TRANSPORT_URL"]
        # one env var flips the whole stack between paid-API and own-GPU
        if os.getenv("AURA_PROVIDER_POLICY"):
            cfg.providers.policy = os.environ["AURA_PROVIDER_POLICY"]
        if os.getenv("AURA_DRIVING_VIDEO"):
            cfg.avatar.driving_video = os.environ["AURA_DRIVING_VIDEO"]
        return cfg
