"""HTTP client for a local Ollama instance.

Uses Ollama's documented HTTP API (never shells out to the `ollama` CLI, per
spec section 6). Every method fails soft: on any network error it returns an
"unavailable" result rather than raising into the caller's hot path, because
the whole point of the local/cloud split is that the system stays usable
when one side is down.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


@dataclass
class OllamaModel:
    name: str
    size: int | None = None
    parameter_size: str | None = None
    context_length: int | None = None
    raw: dict[str, Any] | None = None


class OllamaUnavailableError(Exception):
    pass


class OllamaClient:
    def __init__(self, base_url: str, timeout: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def health(self) -> tuple[bool, str]:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(f"{self.base_url}/")
                if resp.status_code == 200:
                    return True, "ok"
                return False, f"unexpected status {resp.status_code}"
        except httpx.HTTPError as exc:
            return False, f"unreachable: {exc}"

    async def list_models(self) -> list[OllamaModel]:
        """GET /api/tags — the models actually installed and reported by Ollama.

        Raises OllamaUnavailableError on failure; callers must treat that as
        "no local models available" rather than fabricating a list.
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as exc:
            raise OllamaUnavailableError(f"could not reach Ollama at {self.base_url}: {exc}") from exc

        models = []
        for entry in data.get("models", []):
            details = entry.get("details", {}) or {}
            models.append(
                OllamaModel(
                    name=entry.get("name") or entry.get("model", "unknown"),
                    size=entry.get("size"),
                    parameter_size=details.get("parameter_size"),
                    context_length=None,
                    raw=entry,
                )
            )
        return models

    async def chat(self, model: str, messages: list[dict[str, str]], stream: bool = False) -> dict[str, Any]:
        """POST /api/chat — non-streaming by default for background tasks."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{self.base_url}/api/chat",
                    json={"model": model, "messages": messages, "stream": stream},
                )
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPError as exc:
            raise OllamaUnavailableError(f"chat request failed against {self.base_url}: {exc}") from exc
