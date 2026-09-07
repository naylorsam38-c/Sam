"""Unit tests for the RunPod provider (spec section 22.1), using respx to
mock RunPod's GraphQL API — this repository's build environment has no live
RunPod account (see gpu/providers/runpod/provider.py's module docstring),
so this is what verifies the request/response handling actually matches
RunPod's documented API shape; a real account is still required to confirm
that shape hasn't changed (see DEPLOYMENT.md).
"""

from __future__ import annotations

import httpx
import pytest
import respx

from gpu.provider_interface.base import GPUProviderError
from gpu.providers.runpod.provider import GRAPHQL_URL, RunPodProvider


def _provider() -> RunPodProvider:
    return RunPodProvider(api_key="test-key", template_id="tmpl-1", volume_id="vol-1")


def test_missing_api_key_raises_immediately():
    with pytest.raises(GPUProviderError, match="GPU_PROVIDER_API_KEY"):
        RunPodProvider(api_key="", template_id="tmpl-1", volume_id="vol-1")


def test_missing_template_id_raises_immediately():
    with pytest.raises(GPUProviderError, match="GPU_TEMPLATE_ID"):
        RunPodProvider(api_key="key", template_id="", volume_id="vol-1")


async def test_start_without_volume_raises_clear_error():
    provider = RunPodProvider(api_key="key", template_id="tmpl-1", volume_id="")
    with pytest.raises(GPUProviderError, match="GPU_VOLUME_ID"):
        await provider.start()


@respx.mock
async def test_start_deploys_a_new_pod():
    respx.post(url__startswith=GRAPHQL_URL).mock(
        return_value=httpx.Response(200, json={"data": {"podFindAndDeployOnDemand": {
            "id": "pod-123", "imageName": "workstation-cloud-gpu", "machineId": "machine-1",
        }}})
    )
    provider = _provider()
    pod_id = await provider.start()
    assert pod_id == "pod-123"


@respx.mock
async def test_start_resumes_an_existing_pod_on_second_call():
    route = respx.post(url__startswith=GRAPHQL_URL)
    route.side_effect = [
        httpx.Response(200, json={"data": {"podFindAndDeployOnDemand": {"id": "pod-123"}}}),
        httpx.Response(200, json={"data": {"podResume": {"id": "pod-123", "desiredStatus": "RUNNING"}}}),
    ]
    provider = _provider()
    await provider.start()
    pod_id = await provider.start()
    assert pod_id == "pod-123"
    assert route.call_count == 2


@respx.mock
async def test_graphql_errors_raise_gpu_provider_error():
    respx.post(url__startswith=GRAPHQL_URL).mock(
        return_value=httpx.Response(200, json={"errors": [{"message": "invalid api key"}]})
    )
    provider = _provider()
    with pytest.raises(GPUProviderError, match="invalid api key"):
        await provider.start()


@respx.mock
async def test_status_reports_ready_once_runtime_has_a_public_port():
    respx.post(url__startswith=GRAPHQL_URL).mock(side_effect=[
        httpx.Response(200, json={"data": {"podFindAndDeployOnDemand": {"id": "pod-123"}}}),
        httpx.Response(200, json={"data": {"pod": {
            "id": "pod-123", "desiredStatus": "RUNNING", "costPerHr": 0.79,
            "runtime": {"uptimeInSeconds": 42, "ports": [
                {"ip": "1.2.3.4", "privatePort": 11434, "publicPort": 55000, "isIpPublic": True},
            ]},
        }}}),
    ])
    provider = _provider()
    await provider.start()
    status = await provider.status()
    assert status.running is True
    assert status.ready is True
    assert status.endpoint == "http://1.2.3.4:55000"


@respx.mock
async def test_status_not_ready_without_runtime():
    respx.post(url__startswith=GRAPHQL_URL).mock(side_effect=[
        httpx.Response(200, json={"data": {"podFindAndDeployOnDemand": {"id": "pod-123"}}}),
        httpx.Response(200, json={"data": {"pod": {"id": "pod-123", "desiredStatus": "PENDING", "runtime": None}}}),
    ])
    provider = _provider()
    await provider.start()
    status = await provider.status()
    assert status.running is False
    assert status.ready is False
    assert status.endpoint is None


@respx.mock
async def test_get_cost_computes_from_hourly_rate_and_uptime():
    respx.post(url__startswith=GRAPHQL_URL).mock(side_effect=[
        httpx.Response(200, json={"data": {"podFindAndDeployOnDemand": {"id": "pod-123"}}}),
        httpx.Response(200, json={"data": {"pod": {
            "id": "pod-123", "desiredStatus": "RUNNING", "costPerHr": 1.0,
            "runtime": {"uptimeInSeconds": 3600, "ports": []},
        }}}),
    ])
    provider = _provider()
    await provider.start()
    cost = await provider.get_cost()
    assert cost.hourly_rate == 1.0
    assert cost.session_seconds == 3600
    assert cost.estimated_cost == pytest.approx(1.0)


@respx.mock
async def test_stop_and_destroy_are_no_ops_before_any_start():
    provider = _provider()
    await provider.stop()  # must not raise / must not call the API
    await provider.destroy()
    assert respx.calls.call_count == 0


@respx.mock
async def test_network_failure_raises_gpu_provider_error():
    respx.post(url__startswith=GRAPHQL_URL).mock(side_effect=httpx.ConnectError("connection refused"))
    provider = _provider()
    with pytest.raises(GPUProviderError, match="RunPod API request failed"):
        await provider.start()
