"""The worker's only HTTP dependency on the control API: requesting a GPU
start. Everything else (claiming tasks, reading/writing GPU status,
notifications, audit) goes straight to the shared database — only the live
provider connection is exclusive to the control API process (spec: workers
are independent processes; see control/gpu/lifecycle.py's ownership note).
"""

from __future__ import annotations

import httpx

from workstation_core.security import create_access_token


class ControlApiUnavailableError(Exception):
    pass


class ControlApiClient:
    def __init__(self, base_url: str, owner_user_id: str, owner_username: str, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.owner_user_id = owner_user_id
        self.owner_username = owner_username
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        token = create_access_token(self.owner_user_id, self.owner_username)
        return {"Authorization": f"Bearer {token}"}

    async def request_gpu_start(self) -> None:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(f"{self.base_url}/api/gpu/start", headers=self._headers())
                if resp.status_code >= 400:
                    raise ControlApiUnavailableError(f"GPU start request rejected: {resp.status_code} {resp.text}")
        except httpx.HTTPError as exc:
            raise ControlApiUnavailableError(f"could not reach control API at {self.base_url}: {exc}") from exc
