"""Cloud inference adapter.

The rest of the system must not depend on whether the cloud GPU runs Ollama
or vLLM (spec section 6/7). `CloudInferenceClient` normalises both into the
same three operations: health(), list_models(), chat(). Add a new engine by
adding a branch here — nothing else in the codebase changes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from workstation_core.ollama_client import OllamaClient, OllamaUnavailableError


class CloudInferenceUnavailableError(Exception):
    pass


@dataclass
class CloudModel:
    name: str
    context_length: int | None = None
    raw: dict[str, Any] | None = None


class CloudInferenceClient:
    def __init__(self, base_url: str, api_key: str = "", engine: str = "ollama", timeout: float = 30.0):
        self.base_url = base_url.rstrip("/") if base_url else ""
        self.api_key = api_key
        self.engine = engine
        self.timeout = timeout

    @property
    def configured(self) -> bool:
        return bool(self.base_url)

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}

    async def health(self) -> tuple[bool, str]:
        if not self.configured:
            return False, "CLOUD_LLM_BASE_URL not configured"
        if self.engine == "ollama":
            client = OllamaClient(self.base_url, timeout=self.timeout)
            return await client.health()
        if self.engine == "vllm":
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await client.get(f"{self.base_url}/v1/models", headers=self._headers())
                    if resp.status_code == 200:
                        return True, "ok"
                    return False, f"unexpected status {resp.status_code}"
            except httpx.HTTPError as exc:
                return False, f"unreachable: {exc}"
        return False, f"unsupported engine '{self.engine}'"

    async def list_models(self) -> list[CloudModel]:
        if not self.configured:
            raise CloudInferenceUnavailableError("CLOUD_LLM_BASE_URL not configured")

        if self.engine == "ollama":
            client = OllamaClient(self.base_url, timeout=self.timeout)
            try:
                models = await client.list_models()
            except OllamaUnavailableError as exc:
                raise CloudInferenceUnavailableError(str(exc)) from exc
            return [CloudModel(name=m.name, raw=m.raw) for m in models]

        if self.engine == "vllm":
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await client.get(f"{self.base_url}/v1/models", headers=self._headers())
                    resp.raise_for_status()
                    data = resp.json()
            except httpx.HTTPError as exc:
                raise CloudInferenceUnavailableError(f"could not list vLLM models: {exc}") from exc
            return [CloudModel(name=item["id"], raw=item) for item in data.get("data", [])]

        raise CloudInferenceUnavailableError(f"unsupported engine '{self.engine}'")

    async def chat(self, model: str, messages: list[dict[str, str]]) -> dict[str, Any]:
        if not self.configured:
            raise CloudInferenceUnavailableError("CLOUD_LLM_BASE_URL not configured")

        if self.engine == "ollama":
            client = OllamaClient(self.base_url, timeout=self.timeout)
            try:
                return await client.chat(model, messages)
            except OllamaUnavailableError as exc:
                raise CloudInferenceUnavailableError(str(exc)) from exc

        if self.engine == "vllm":
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await client.post(
                        f"{self.base_url}/v1/chat/completions",
                        headers=self._headers(),
                        json={"model": model, "messages": messages},
                    )
                    resp.raise_for_status()
                    return resp.json()
            except httpx.HTTPError as exc:
                raise CloudInferenceUnavailableError(f"chat request failed: {exc}") from exc

        raise CloudInferenceUnavailableError(f"unsupported engine '{self.engine}'")
