"""GPUProvider — the pluggable cloud-GPU contract (spec section 7).

Every concrete provider (RunPod, Vast, Lambda Labs, ...) implements this
interface. The GPU lifecycle manager (apps/control/src/control/gpu) drives
providers exclusively through these methods, so adding a new cloud never
touches the lifecycle state machine, task routing, or cost-control code.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ProviderStatus:
    """What the provider itself reports right now — the lifecycle manager
    maps this onto the GPUStatus state machine, it does not trust the
    provider to know about that state machine."""

    running: bool
    ready: bool
    instance_id: str | None
    endpoint: str | None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class ProviderCost:
    hourly_rate: float
    session_seconds: float
    estimated_cost: float
    currency: str = "USD"


class GPUProviderError(Exception):
    """Raised for any provider-side failure. Never swallowed silently —
    the lifecycle manager turns this into GPUStatus.ERROR plus a
    notification (spec rule: 'failures must be explicit and observable')."""


class GPUProvider(ABC):
    name: str = "base"

    @abstractmethod
    async def provision(self) -> str:
        """Create (but do not necessarily start) the persistent resources
        this provider needs (e.g. a volume). Returns a provider-specific
        resource id. Idempotent where the provider allows it."""

    @abstractmethod
    async def start(self) -> str:
        """Start (or resume) the GPU instance. Returns the instance id.
        Must not block until ready — callers poll status()/health()."""

    @abstractmethod
    async def stop(self) -> None:
        """Stop the instance. Must not destroy persistent storage."""

    @abstractmethod
    async def destroy(self) -> None:
        """Tear down the instance and any resources provisioned by
        provision(). Used for hard resets / re-provisioning, not part of
        the normal idle-shutdown path."""

    @abstractmethod
    async def status(self) -> ProviderStatus:
        """Point-in-time status as reported by the provider API."""

    @abstractmethod
    async def health(self) -> tuple[bool, str]:
        """Application-level health check against the inference endpoint
        itself (not just 'is the VM up'), used to gate READY."""

    @abstractmethod
    async def get_cost(self) -> ProviderCost:
        """Best-effort cost estimate. Providers that expose real billing
        data should use it; otherwise this must be computed from
        (session duration * configured hourly rate) — never fabricated
        as zero."""

    @abstractmethod
    def get_endpoint(self) -> str | None:
        """The inference base URL once known, else None."""

    @abstractmethod
    def metadata(self) -> dict[str, Any]:
        """Provider-specific debugging/audit metadata."""
