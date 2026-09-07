"""RunPod GPU provider — the first real cloud implementation (spec section 7).

Talks to RunPod's GraphQL API (https://api.runpod.io/graphql). Requires:
  GPU_PROVIDER_API_KEY  - RunPod API key
  GPU_TEMPLATE_ID       - a RunPod pod template id (pre-built with the
                          inference engine + CUDA installed; see gpu/image)
  GPU_VOLUME_ID         - an existing RunPod network volume id, created once
                          during install-phase B so models/data persist
                          across pod restarts (spec section 18)

This module makes real network calls and is exercised in this repository's
test suite via mocked HTTP (tests/unit/test_gpu_runpod.py) since no live
RunPod account is available in the build environment. It has not been
verified against a real RunPod account — that verification is a required
step of install Phase B and is called out explicitly in BUILD_REPORT.md and
DEPLOYMENT.md rather than assumed.
"""

from __future__ import annotations

from typing import Any

import httpx

from gpu.provider_interface.base import GPUProvider, GPUProviderError, ProviderCost, ProviderStatus

GRAPHQL_URL = "https://api.runpod.io/graphql"


class RunPodProvider(GPUProvider):
    name = "runpod"

    def __init__(
        self,
        api_key: str,
        template_id: str,
        volume_id: str,
        gpu_type_id: str = "NVIDIA RTX A5000",
        timeout: float = 30.0,
    ):
        if not api_key:
            raise GPUProviderError("GPU_PROVIDER_API_KEY is required for the runpod provider")
        if not template_id:
            raise GPUProviderError("GPU_TEMPLATE_ID is required for the runpod provider")
        self.api_key = api_key
        self.template_id = template_id
        self.volume_id = volume_id
        self.gpu_type_id = gpu_type_id
        self.timeout = timeout
        self._pod_id: str | None = None
        self._last_pod_data: dict[str, Any] = {}

    async def _graphql(self, query: str, variables: dict[str, Any]) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{GRAPHQL_URL}?api_key={self.api_key}",
                    json={"query": query, "variables": variables},
                )
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as exc:
            raise GPUProviderError(f"RunPod API request failed: {exc}") from exc

        if data.get("errors"):
            raise GPUProviderError(f"RunPod API returned errors: {data['errors']}")
        return data.get("data", {})

    async def provision(self) -> str:
        if not self.volume_id:
            raise GPUProviderError(
                "No GPU_VOLUME_ID configured. Create a persistent RunPod network volume "
                "during install Phase B before starting the GPU (spec section 21, Phase B step 2)."
            )
        return self.volume_id

    async def start(self) -> str:
        await self.provision()

        if self._pod_id:
            query = """
            mutation resumePod($input: PodResumeInput!) {
              podResume(input: $input) { id desiredStatus }
            }
            """
            data = await self._graphql(query, {"input": {"podId": self._pod_id}})
            self._pod_id = data["podResume"]["id"]
            return self._pod_id

        query = """
        mutation deployPod($input: PodFindAndDeployOnDemandInput!) {
          podFindAndDeployOnDemand(input: $input) { id imageName machineId }
        }
        """
        variables = {
            "input": {
                "templateId": self.template_id,
                "networkVolumeId": self.volume_id,
                "gpuTypeId": self.gpu_type_id,
                "cloudType": "SECURE",
                "gpuCount": 1,
            }
        }
        data = await self._graphql(query, variables)
        self._pod_id = data["podFindAndDeployOnDemand"]["id"]
        return self._pod_id

    async def stop(self) -> None:
        if not self._pod_id:
            return
        query = """
        mutation stopPod($input: PodStopInput!) {
          podStop(input: $input) { id desiredStatus }
        }
        """
        await self._graphql(query, {"input": {"podId": self._pod_id}})

    async def destroy(self) -> None:
        if not self._pod_id:
            return
        query = """
        mutation terminatePod($input: PodTerminateInput!) {
          podTerminate(input: $input)
        }
        """
        await self._graphql(query, {"input": {"podId": self._pod_id}})
        self._pod_id = None
        self._last_pod_data = {}

    async def _fetch_pod(self) -> dict[str, Any]:
        if not self._pod_id:
            return {}
        query = """
        query getPod($podId: String!) {
          pod(input: {podId: $podId}) {
            id
            desiredStatus
            costPerHr
            runtime { uptimeInSeconds ports { ip privatePort publicPort isIpPublic } }
          }
        }
        """
        data = await self._graphql(query, {"podId": self._pod_id})
        self._last_pod_data = data.get("pod") or {}
        return self._last_pod_data

    async def status(self) -> ProviderStatus:
        if not self._pod_id:
            return ProviderStatus(running=False, ready=False, instance_id=None, endpoint=None)

        pod = await self._fetch_pod()
        runtime = pod.get("runtime")
        running = pod.get("desiredStatus") == "RUNNING" and runtime is not None
        endpoint = self.get_endpoint()
        ready = running and endpoint is not None
        return ProviderStatus(running=running, ready=ready, instance_id=self._pod_id, endpoint=endpoint, raw=pod)

    async def health(self) -> tuple[bool, str]:
        endpoint = self.get_endpoint()
        if not endpoint:
            return False, "pod has no reachable endpoint yet"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(endpoint)
                # Any HTTP response means the process behind the port is
                # alive; engine-specific health is checked separately by
                # CloudInferenceClient once this coarse check passes.
                return resp.status_code < 500, f"http {resp.status_code}"
        except httpx.HTTPError as exc:
            return False, f"unreachable: {exc}"

    async def get_cost(self) -> ProviderCost:
        pod = self._last_pod_data or await self._fetch_pod()
        runtime = pod.get("runtime") or {}
        hourly_rate = float(pod.get("costPerHr") or 0.0)
        session_seconds = float(runtime.get("uptimeInSeconds") or 0.0)
        return ProviderCost(
            hourly_rate=hourly_rate,
            session_seconds=session_seconds,
            estimated_cost=hourly_rate * (session_seconds / 3600.0),
        )

    def get_endpoint(self) -> str | None:
        runtime = self._last_pod_data.get("runtime") if self._last_pod_data else None
        if not runtime:
            return None
        for port in runtime.get("ports", []):
            if port.get("isIpPublic") and port.get("publicPort"):
                return f"http://{port['ip']}:{port['publicPort']}"
        return None

    def metadata(self) -> dict[str, Any]:
        return {"provider": "runpod", "pod_id": self._pod_id, "raw": self._last_pod_data}
