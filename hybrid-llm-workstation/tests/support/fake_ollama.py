"""A real local HTTP server that speaks enough of the Ollama protocol
(GET /, GET /api/tags, POST /api/chat) to exercise workstation_core's
OllamaClient/CloudInferenceClient over an actual socket, instead of mocking
the HTTP layer. Shared by control, worker, and top-level integration tests.
"""

from __future__ import annotations

import json
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def _make_handler(models: list[str]):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def _json(self, payload, status=200):
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
                self._json({"models": [{"name": m, "size": 1, "details": {"parameter_size": "3B"}} for m in models]})
            else:
                self._json({"error": "not found"}, status=404)

        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length) if length else b"{}"
            payload = json.loads(raw or b"{}")
            if self.path == "/api/chat":
                self._json({"model": payload.get("model"), "message": {"role": "assistant", "content": "hi"}, "done": True})
            else:
                self._json({"error": "not found"}, status=404)

    return Handler


@contextmanager
def fake_ollama_server(models: list[str] | None = None):
    server = ThreadingHTTPServer(("127.0.0.1", 0), _make_handler(models or ["llama3.2:latest"]))
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.shutdown()
        server.server_close()
