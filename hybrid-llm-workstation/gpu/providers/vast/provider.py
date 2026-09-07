"""Vast.ai provider — interface placeholder.

Deliberately NOT implemented. Per spec section 7 ("additional providers
must be pluggable") and the operational rule "never use simulation/canned
responses as acceptance evidence", this stub raises rather than pretending
to support Vast.ai. Implement by following the pattern in
gpu/providers/runpod/provider.py against Vast's REST API
(https://vast.ai/api/v0/), then register it in gpu/registry.py.
"""

from __future__ import annotations

from typing import Any

from gpu.provider_interface.base import GPUProvider, ProviderCost, ProviderStatus

_NOT_IMPLEMENTED = (
    "The Vast.ai provider is a defined interface stub only — it has not been "
    "implemented. Select GPU_PROVIDER=runpod or GPU_PROVIDER=mock, or "
    "implement gpu/providers/vast/provider.py against gpu.provider_interface.base.GPUProvider."
)


class VastProvider(GPUProvider):
    name = "vast"

    def __init__(self, *_args, **_kwargs):
        raise NotImplementedError(_NOT_IMPLEMENTED)

    async def provision(self) -> str:  # pragma: no cover - unreachable, __init__ raises
        raise NotImplementedError(_NOT_IMPLEMENTED)

    async def start(self) -> str:  # pragma: no cover
        raise NotImplementedError(_NOT_IMPLEMENTED)

    async def stop(self) -> None:  # pragma: no cover
        raise NotImplementedError(_NOT_IMPLEMENTED)

    async def destroy(self) -> None:  # pragma: no cover
        raise NotImplementedError(_NOT_IMPLEMENTED)

    async def status(self) -> ProviderStatus:  # pragma: no cover
        raise NotImplementedError(_NOT_IMPLEMENTED)

    async def health(self) -> tuple[bool, str]:  # pragma: no cover
        raise NotImplementedError(_NOT_IMPLEMENTED)

    async def get_cost(self) -> ProviderCost:  # pragma: no cover
        raise NotImplementedError(_NOT_IMPLEMENTED)

    def get_endpoint(self) -> str | None:  # pragma: no cover
        raise NotImplementedError(_NOT_IMPLEMENTED)

    def metadata(self) -> dict[str, Any]:  # pragma: no cover
        raise NotImplementedError(_NOT_IMPLEMENTED)
