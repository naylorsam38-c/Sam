from __future__ import annotations

from dataclasses import dataclass
import json
import os
import urllib.request
from typing import Protocol


class ModelClient(Protocol):
    """Exactly one model invocation per call()."""

    def call(self, system: str, user: str) -> str:
        ...


@dataclass
class OpenAICompatibleClient:
    """Minimal stdlib-only OpenAI-compatible chat client."""

    model: str
    base_url: str
    api_key: str
    timeout: float = 120.0

    @classmethod
    def from_env(cls) -> "OpenAICompatibleClient":
        return cls(
            model=os.getenv("SPEC_WRITER_MODEL", "gpt-5.6"),
            base_url=os.getenv(
                "SPEC_WRITER_BASE_URL",
                "https://api.openai.com/v1/chat/completions",
            ),
            api_key=os.getenv("SPEC_WRITER_API_KEY", ""),
            timeout=float(os.getenv("SPEC_WRITER_MODEL_TIMEOUT", "120")),
        )

    def call(self, system: str, user: str) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        body = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        request = urllib.request.Request(
            self.base_url,
            data=body,
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            raise RuntimeError(f"model call failed: {exc}") from exc

        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("model response did not contain choices[0].message.content") from exc
