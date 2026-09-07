"""A real local HTTP server standing in for the local execution agent, for
control-plane tests that exercise the approval -> execute proxy without
depending on the actual local-agent implementation (which independently
re-verifies signatures and policy; that behavior is tested against the real
agent in local-agent/tests and tests/integration).
"""

from __future__ import annotations

import json
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def _make_handler(received: list):
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
            if self.path == "/health":
                self._json({"status": "ok"})
            else:
                self._json({"error": "not found"}, status=404)

        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length) if length else b"{}"
            payload = json.loads(raw or b"{}")
            if self.path == "/execute":
                received.append(payload)
                self._json({
                    "request_id": payload["request_id"],
                    "status": "COMPLETED",
                    "stdout": f"ran {payload['operation']}",
                    "stderr": "",
                    "exit_code": 0,
                    "result": {},
                    "timestamp": payload["timestamp"],
                })
            else:
                self._json({"error": "not found"}, status=404)

    return Handler


@contextmanager
def fake_agent_server():
    received: list = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), _make_handler(received))
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{port}", received
    finally:
        server.shutdown()
        server.server_close()
