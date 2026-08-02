"""
Provider registry — the switch that makes "API or self-hosted" a config line.

Callers ask for a *kind* ("tts") and a *policy*, and get back a working provider.
The registry:

  1. builds the candidate chain from config (explicit engine first, then the
     policy's preference order, then the guaranteed local fallback),
  2. drops candidates whose licence is not cleared for commercial use, unless
     the caller has explicitly opted out of commercial mode,
  3. drops candidates whose requirements are unmet (no API key, no GPU, no
     package) — reporting exactly what was missing,
  4. calls `setup()` and returns the first one that actually starts.

The result: the same session code runs on Cartesia today and Kokoro-on-your-own-
4090 tomorrow, with no diff outside `config/aura.yaml`.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .base import ProviderInfo, ProviderUnavailable, Tier
from ..worker import log

# kind -> {name -> zero-arg factory}. Populated by `register()`.
_REGISTRY: dict[str, dict[str, Callable[..., Any]]] = {}

# Preference order per policy. First entry that can run, wins.
POLICIES: dict[str, dict[str, list[str]]] = {
    # best available quality; bills per minute of use
    "api": {
        "tts":    ["cartesia", "elevenlabs", "kokoro", "espeak"],
        "stt":    ["deepgram", "faster-whisper", "null"],
        "avatar": ["simli", "musetalk", "fallback"],
    },
    # no per-minute fees; bills per GPU-hour
    "selfhosted": {
        "tts":    ["kokoro", "espeak"],
        "stt":    ["faster-whisper", "null"],
        "avatar": ["musetalk", "fallback"],
    },
    # prefer free local, borrow the API only when local can't run
    "auto": {
        "tts":    ["kokoro", "cartesia", "elevenlabs", "espeak"],
        "stt":    ["faster-whisper", "deepgram", "null"],
        "avatar": ["musetalk", "simli", "fallback"],
    },
    # never leaves the machine, never bills
    "offline": {
        "tts":    ["espeak"],
        "stt":    ["null"],
        "avatar": ["fallback"],
    },
}


def register(kind: str, name: str, factory: Callable[..., Any]) -> None:
    _REGISTRY.setdefault(kind, {})[name] = factory


def available(kind: str) -> list[str]:
    return sorted(_REGISTRY.get(kind, {}))


@dataclass
class Resolution:
    """What the registry picked, and why everything else was skipped. Surfaced
    on /healthz so an operator can see the real engine, not the configured one."""
    kind: str
    chosen: str | None
    info: ProviderInfo | None
    skipped: list[tuple[str, str]]      # (candidate, reason)

    def summary(self) -> dict:
        return {"kind": self.kind, "chosen": self.chosen,
                "tier": self.info.tier if self.info else None,
                "licence": self.info.licence if self.info else None,
                "cost_per_min": round(self.info.cost.effective_per_minute(), 4)
                if self.info else None,
                "skipped": [{"provider": n, "reason": r} for n, r in self.skipped]}


def _chain(kind: str, policy: str, engine: str | None) -> list[str]:
    order = list(POLICIES.get(policy, POLICIES["auto"]).get(kind, []))
    if engine and engine != "auto":
        # explicit engine wins, but the chain stays as the safety net
        order = [engine] + [o for o in order if o != engine]
    return order


async def resolve(kind: str, *, policy: str = "auto", engine: str | None = None,
                  commercial: bool = True, **kwargs) -> tuple[Any, Resolution]:
    """Return (provider, resolution) for the first candidate that starts.

    Raises RuntimeError only if the entire chain fails — which should be
    impossible in practice, because every chain ends in a dependency-free
    fallback.
    """
    skipped: list[tuple[str, str]] = []
    registered = _REGISTRY.get(kind, {})

    for name in _chain(kind, policy, engine):
        factory = registered.get(name)
        if factory is None:
            skipped.append((name, "not registered"))
            continue

        try:
            provider = factory(**kwargs)
        except Exception as e:
            skipped.append((name, f"construction failed: {e!r}"))
            continue

        info: ProviderInfo = provider.info
        if commercial and not info.commercial:
            skipped.append((name, f"licence not cleared for commercial use "
                                  f"(code={info.licence}, weights={info.weight_licence})"))
            continue

        missing = info.requires.missing()
        if missing:
            skipped.append((name, "missing " + ", ".join(missing)))
            continue

        try:
            await provider.setup()
        except ProviderUnavailable as e:
            skipped.append((name, f"unavailable: {e}"))
            continue
        except Exception as e:
            skipped.append((name, f"setup failed: {e!r}"))
            continue

        res = Resolution(kind, name, info, skipped)
        log("registry", "info", "provider selected", kind=kind, provider=name,
            tier=info.tier, policy=policy,
            cost_per_min=round(info.cost.effective_per_minute(), 4),
            skipped=[f"{n}: {r}" for n, r in skipped])
        return provider, res

    raise RuntimeError(
        f"no usable {kind} provider under policy '{policy}'. Tried: "
        + "; ".join(f"{n} ({r})" for n, r in skipped))


def estimate_cost_per_minute(resolutions: list[Resolution],
                             utilisation: float = 1.0) -> dict:
    """Blended $/conversation-minute across the resolved stack.

    For self-hosted providers the GPU bills whether or not anyone is talking, so
    `utilisation` (fraction of wall-clock spent producing output) is what makes
    the API and GPU numbers comparable. At 10% utilisation a $0.50/hr GPU costs
    ~$0.083/min of actual conversation — worse than most APIs.
    """
    breakdown, total = {}, 0.0
    for r in resolutions:
        if not r.info:
            continue
        c = r.info.cost.effective_per_minute(utilisation)
        # a GPU shared by several stages is billed once, not once per stage
        if r.info.cost.gpu_hour and any(
                x.info and x.info.cost.gpu_hour and x.kind < r.kind
                for x in resolutions):
            c = 0.0
        breakdown[r.kind] = {"provider": r.chosen, "tier": r.info.tier,
                             "per_minute": round(c, 4)}
        total += c
    return {"per_minute_usd": round(total, 4),
            "per_hour_usd": round(total * 60, 2),
            "utilisation": utilisation, "breakdown": breakdown}
