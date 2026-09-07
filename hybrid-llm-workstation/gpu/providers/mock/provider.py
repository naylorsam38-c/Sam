"""Mock GPU provider: a real, local, Ollama-protocol-compatible HTTP server
standing in for a rented cloud GPU.

This is what GPU_PROVIDER=mock uses for local development and for this
project's own automated tests. It is NOT a fake return value hard-coded
into the client — it is an actual process listening on a real port that the
CloudInferenceClient talks to over real HTTP, so the lifecycle manager,
worker, and cloud client are exercised exactly as they would be against a
real provider. It must never be selected in a production GPU_PROVIDER
setting (config/providers.yaml documents this).
"""

from __future__ import annotations

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import httpx

from gpu.provider_interface.base import GPUProvider, GPUProviderError, ProviderCost, ProviderStatus


def _make_handler(model_name: str) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):  # silence stdout spam in tests
            pass

        def _json(self, payload: dict[str, Any], status: int = 200):
            body = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path == "/":
                self._json({"status": "Ollama is running"})
            elif self.path == "/api/tags":
                self._json({"models": [{"name": model_name, "size": 1234, "details": {"parameter_size": "70B"}}]})
            else:
                self._json({"error": "not found"}, status=404)

        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length) if length else b"{}"
            try:
                payload = json.loads(raw or b"{}")
            except json.JSONDecodeError:
                payload = {}
            if self.path == "/api/chat":
                last_user = next(
                    (m.get("content", "") for m in reversed(payload.get("messages", [])) if m.get("role") == "user"),
                    "",
                )
                self._json(
                    {
                        "model": payload.get("model", model_name),
                        "message": {
                            "role": "assistant",
                            "content": f"[mock cloud GPU response] you said: {last_user}",
                        },
                        "done": True,
                    }
                )
            else:
                self._json({"error": "not found"}, status=404)

    return Handler


class MockGPUProvider(GPUProvider):
    name = "mock"

    def __init__(self, boot_delay_seconds: float = 0.0, hourly_rate: float = 0.50, model_name: str = "mock-cloud-model"):
        self.boot_delay_seconds = boot_delay_seconds
        self.hourly_rate = hourly_rate
        self.model_name = model_name
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._port: int | None = None
        self._started_at: float | None = None
        self._provisioned = False
        self._instance_id: str | None = None
        self._destroyed_volume = False

    async def provision(self) -> str:
        self._provisioned = True
        return "mock-volume-1"

    async def start(self) -> str:
        if not self._provisioned:
            await self.provision()
        if self._server is None:
            handler = _make_handler(self.model_name)
            self._server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
            self._port = self._server.server_address[1]
            self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
            self._thread.start()
        self._started_at = time.time()
        self._instance_id = self._instance_id or "mock-instance-1"
        return self._instance_id

    async def stop(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
            self._thread = None
            self._port = None
        self._started_at = None

    async def destroy(self) -> None:
        await self.stop()
        self._instance_id = None
        self._provisioned = False

    async def status(self) -> ProviderStatus:
        running = self._server is not None
        ready = running and self._started_at is not None and (time.time() - self._started_at) >= self.boot_delay_seconds
        return ProviderStatus(
            running=running,
            ready=ready,
            instance_id=self._instance_id,
            endpoint=self.get_endpoint(),
            raw={"port": self._port},
        )

    async def health(self) -> tuple[bool, str]:
        if self._server is None:
            return False, "mock GPU is not running"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.get_endpoint()}/")
                if resp.status_code == 200:
                    return True, "ok"
                return False, f"unexpected status {resp.status_code}"
        except httpx.HTTPError as exc:
            raise GPUProviderError(f"mock provider health check failed: {exc}") from exc

    async def get_cost(self) -> ProviderCost:
        session_seconds = (time.time() - self._started_at) if self._started_at else 0.0
        return ProviderCost(
            hourly_rate=self.hourly_rate,
            session_seconds=session_seconds,
            estimated_cost=self.hourly_rate * (session_seconds / 3600.0),
        )

    def get_endpoint(self) -> str | None:
        if self._port is None:
            return None
        return f"http://127.0.0.1:{self._port}"

    def metadata(self) -> dict[str, Any]:
        return {"provider": "mock", "port": self._port, "instance_id": self._instance_id}
