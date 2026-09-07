"""Lambda Labs (Lambda Cloud) provider — interface placeholder.

Named `lambdalabs` rather than `lambda` because `lambda` is a reserved
Python keyword and cannot be a package name; this is a naming
implementation detail only (see docs/ARCHITECTURE.md), the on-disk
directory still matches the provider's identity.

Deliberately NOT implemented — see gpu/providers/vast/provider.py for the
rationale. Implement against Lambda Cloud's REST API
(https://cloud.lambdalabs.com/api/v1/) following the RunPod provider as a
template, then register it in gpu/registry.py.
"""

from __future__ import annotations

from typing import Any

from gpu.provider_interface.base import GPUProvider, ProviderCost, ProviderStatus

_NOT_IMPLEMENTED = (
    "The Lambda Labs provider is a defined interface stub only — it has not "
    "been implemented. Select GPU_PROVIDER=runpod or GPU_PROVIDER=mock, or "
    "implement gpu/providers/lambdalabs/provider.py against "
    "gpu.provider_interface.base.GPUProvider."
)


class LambdaLabsProvider(GPUProvider):
    name = "lambdalabs"

    def __init__(self, *_args, **_kwargs):
        raise NotImplementedError(_NOT_IMPLEMENTED)

    async def provision(self) -> str:  # pragma: no cover
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
