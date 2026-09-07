"""HTTP client the control plane uses to reach the local execution agent.

Every request is HMAC-signed (workstation_core.security) using
EXECUTION_AGENT_TOKEN as the shared secret. The agent independently
verifies the signature and re-applies its own policy — this client cannot
make the agent do anything the agent itself doesn't also agree to (spec
section 15/17: defence in depth).
"""

from __future__ import annotations

import time
import uuid
from typing import Any

import httpx

from workstation_core.security import sign_agent_request


class AgentUnavailableError(Exception):
    pass


class AgentClient:
    def __init__(self, base_url: str, token: str, timeout: float = 120.0):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout

    async def execute(
        self, *, operation: str, parameters: dict[str, Any], working_directory: str | None,
        task_id: str | None, requested_by: str, approval_token: str | None = None,
    ) -> dict[str, Any]:
        request_id = str(uuid.uuid4())
        timestamp = int(time.time())
        signature = sign_agent_request(request_id, operation, timestamp, self.token)

        payload = {
            "request_id": request_id,
            "task_id": task_id,
            "operation": operation,
            "parameters": parameters,
            "working_directory": working_directory,
            "requested_by": requested_by,
            "timestamp": timestamp,
            "signature": signature,
            "approval_token": approval_token,
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(f"{self.base_url}/execute", json=payload)
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPError as exc:
            raise AgentUnavailableError(f"could not reach local execution agent at {self.base_url}: {exc}") from exc

    async def health(self) -> tuple[bool, str]:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{self.base_url}/health")
                if resp.status_code == 200:
                    return True, "ok"
                return False, f"unexpected status {resp.status_code}"
        except httpx.HTTPError as exc:
            return False, f"unreachable: {exc}"
