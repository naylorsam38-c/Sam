"""Resolve the configured GPU_PROVIDER name into a GPUProvider instance.

This is the only place in the codebase that imports a concrete provider
module — everything else (lifecycle manager, worker, control API) depends
only on gpu.provider_interface.base.GPUProvider.
"""

from __future__ import annotations

from gpu.provider_interface.base import GPUProvider, GPUProviderError


def get_provider(
    provider_name: str,
    api_key: str = "",
    template_id: str = "",
    volume_id: str = "",
    hourly_rate: float = 0.50,
) -> GPUProvider:
    if provider_name == "mock":
        from gpu.providers.mock.provider import MockGPUProvider

        return MockGPUProvider(hourly_rate=hourly_rate)

    if provider_name == "runpod":
        from gpu.providers.runpod.provider import RunPodProvider

        return RunPodProvider(api_key=api_key, template_id=template_id, volume_id=volume_id)

    if provider_name == "vast":
        from gpu.providers.vast.provider import VastProvider

        return VastProvider()

    if provider_name == "lambdalabs":
        from gpu.providers.lambdalabs.provider import LambdaLabsProvider

        return LambdaLabsProvider()

    raise GPUProviderError(
        f"Unknown GPU_PROVIDER '{provider_name}'. Valid options: mock, runpod, vast, lambdalabs."
    )
