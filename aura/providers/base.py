"""
Provider contracts.

Every swappable engine (TTS, STT, avatar renderer) is a *provider*. A provider
declares, up front and machine-readably:

  - `tier`      : where it runs and how it bills (api | selfhosted | fallback)
  - `licence`   : the licence of its code AND its weights
  - `cost`      : the honest unit cost, so the registry can report $/minute
  - `requires`  : env vars, python packages and hardware it needs to work

That declaration is the whole point. It lets `registry.resolve()` pick the best
provider that can actually run *here*, degrade to the next one when it can't,
and refuse anything the licence gate has not cleared — without any caller
knowing which engine it ended up with.

Nothing in this module does I/O or imports a heavy dependency.
"""
from __future__ import annotations

import importlib.util
import os
import shutil
from dataclasses import dataclass, field
from typing import Iterator, Protocol, runtime_checkable

import numpy as np


# ── how a provider bills ────────────────────────────────────────────────────
class Tier:
    API = "api"                 # pay per unit of usage, no idle cost
    SELFHOSTED = "selfhosted"   # pay per GPU-hour, no per-unit cost
    FALLBACK = "fallback"       # free, always works, lowest quality


@dataclass(frozen=True)
class Cost:
    """Honest unit cost. `per_minute` is USD per minute of *output* produced.

    Self-hosted providers set `per_minute=0.0` and record `gpu_hour` instead —
    the registry converts that to an effective per-minute figure once you tell
    it your expected utilisation, so the two tiers can be compared fairly.
    """
    per_minute: float = 0.0
    gpu_hour: float = 0.0
    note: str = ""

    def effective_per_minute(self, utilisation: float = 1.0) -> float:
        """Blended $/min. `utilisation` is the fraction of wall-clock time the
        GPU is actually producing output — idle GPU time still bills."""
        if self.per_minute:
            return self.per_minute
        if self.gpu_hour:
            u = max(0.01, min(1.0, utilisation))
            return self.gpu_hour / 60.0 / u
        return 0.0


@dataclass(frozen=True)
class Requires:
    """What must be present for this provider to run."""
    env: tuple[str, ...] = ()          # env vars that must be set + non-empty
    packages: tuple[str, ...] = ()     # importable python modules
    binaries: tuple[str, ...] = ()     # executables on PATH
    gpu: bool = False                  # needs a visible CUDA device

    def missing(self) -> list[str]:
        """Return every unmet requirement, so failures explain themselves."""
        out: list[str] = []
        out += [f"env:{k}" for k in self.env if not os.getenv(k)]
        out += [f"pkg:{p}" for p in self.packages
                if importlib.util.find_spec(p) is None]
        out += [f"bin:{b}" for b in self.binaries if not shutil.which(b)]
        if self.gpu and not _cuda_available():
            out.append("gpu:cuda")
        return out


def _cuda_available() -> bool:
    """True only if a CUDA device is actually visible. Never raises."""
    if os.getenv("AURA_FORCE_GPU") == "1":
        return True
    try:
        import torch
        return bool(torch.cuda.is_available())
    except Exception:
        return False


@dataclass(frozen=True)
class ProviderInfo:
    name: str
    tier: str
    licence: str                       # code licence
    weight_licence: str | None = None  # weights, when they differ from the code
    cost: Cost = field(default_factory=Cost)
    requires: Requires = field(default_factory=Requires)
    quality: int = 1                   # 0..5, rough and self-declared
    latency_ms: int = 0                # typical time-to-first-output
    note: str = ""
    separate_process: bool = False     # invoked via exec, never linked

    @property
    def commercial(self) -> bool:
        """Whether both licences permit commercial use. Conservative: an
        unknown or missing licence is treated as NOT cleared.

        `separate_process=True` clears a copyleft licence (GPL/LGPL) because the
        component is exec'd as its own process and exchanges data over a pipe —
        mere aggregation, so the copyleft does not reach our source. It does NOT
        clear a non-commercial licence: no boundary makes 'you may not sell this'
        go away.
        """
        from .licences import commercial_ok, is_noncommercial

        def ok(lic: str | None) -> bool:
            if lic is None:
                return True
            if is_noncommercial(lic):
                return False            # never rescuable by aggregation
            return commercial_ok(lic) or self.separate_process

        return ok(self.licence) and ok(self.weight_licence)


class ProviderUnavailable(RuntimeError):
    """Raised by `setup()` when a provider's requirements are not met. The
    registry catches this and moves to the next candidate."""


# ── the three provider contracts ────────────────────────────────────────────
@runtime_checkable
class TTSProvider(Protocol):
    info: ProviderInfo

    async def setup(self) -> None:
        """Load models / open clients. Raise ProviderUnavailable if it can't."""

    async def synthesize(self, text: str, wav_path: str, *, voice: str,
                         sample_rate: int) -> str:
        """Write speech for `text` to `wav_path` and return the path."""

    async def close(self) -> None: ...


@runtime_checkable
class STTProvider(Protocol):
    info: ProviderInfo

    async def setup(self) -> None: ...

    async def transcribe(self, wav_path: str) -> "Transcript":
        """Transcribe one utterance."""

    async def close(self) -> None: ...


@dataclass
class Transcript:
    text: str
    uncertain: bool = False
    no_speech: bool = False
    segments: list[str] = field(default_factory=list)


@runtime_checkable
class AvatarProvider(Protocol):
    """Turns speech audio into avatar video frames.

    `speaking_frames` yields (bgr_frame, audio_pts_seconds). The PTS MUST be
    derived from the audio timeline — audio is the master clock and the drift
    meter compares against exactly this value.
    """
    info: ProviderInfo

    async def setup(self) -> None: ...

    def idle_frame(self, state: str, t: float) -> np.ndarray:
        """One 'alive' frame for the given session state."""

    def speaking_frames(self, wav_path: str) -> Iterator[tuple[np.ndarray, float]]:
        ...

    async def close(self) -> None: ...
