"""The Hands session API — a real HTTP server over the real engine.

Stdlib only, to match the rest of this repository. Every request opens its
own connection to the real database, so the server holds no session state
in memory and a restart loses nothing.

The API deliberately cannot express "do this thing to that document". A
caller may start a session against a defined workflow, supply information,
decide an approval, and ask the engine to continue. What actually happens
is decided by the workflow and the engine, never by the request body.
"""

import base64
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from . import config, documents, engine
from . import session as sess
from . import store, trust_gate, workflow


#: The operator screen. Served without a token because it is the page that
#: asks for one; every call it then makes is authenticated like any other.
WEB_ROOT = Path(__file__).resolve().parents[1] / "web"
STATIC = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "application/javascript; charset=utf-8"),
    "/style.css": ("style.css", "text/css; charset=utf-8"),
}


class ApiError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = message


def _handler_class(data_root, token):
    class Handler(BaseHTTPRequestHandler):
        server_version = "Hands/1.0"
        protocol_version = "HTTP/1.1"

        # ---- plumbing ------------------------------------------------
        def log_message(self, fmt, *args):  # keep the test output readable
            pass

        def _authorised(self):
            if not config.REQUIRE_AUTH:
                return True
            header = self.headers.get("Authorization", "")
            return header == f"Bearer {token}"

        def _body(self):
            length = int(self.headers.get("Content-Length") or 0)
            if not length:
                return {}
            raw = self.rfile.read(length)
            try:
                return json.loads(raw.decode("utf-8"))
            except ValueError:
                raise ApiError(400, "body must be JSON")

        def _send(self, status, payload, raw=None, content_type="application/json"):
            body = raw if raw is not None else json.dumps(payload, sort_keys=True).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _dispatch(self, method):
            path = urlparse(self.path).path
            if method == "GET" and path in STATIC:
                name, ctype = STATIC[path]
                return self._send(200, None, (WEB_ROOT / name).read_bytes(), ctype)
            if not self._authorised():
                return self._send(401, {"error": "unauthorised"})
            path = urlparse(self.path).path.rstrip("/") or "/"
            conn = store.connect(data_root)
            try:
                status, payload, raw, ctype = route(conn, method, path, self._body() if method == "POST" else {},
                                                    data_root)
                self._send(status, payload, raw, ctype)
            except ApiError as err:
                self._send(err.status, {"error": err.message})
            except Exception as err:  # a real failure is reported, never swallowed
                self._send(500, {"error": f"{type(err).__name__}: {err}"})
            finally:
                conn.close()

        def do_GET(self):
            self._dispatch("GET")

        def do_POST(self):
            self._dispatch("POST")

    return Handler


def route(conn, method, path, body, data_root):
    """Returns (status, json_payload, raw_bytes, content_type)."""
    parts = [p for p in path.split("/") if p]

    if method == "GET" and parts == ["api", "health"]:
        return 200, {"ok": True, "workflows": sorted(workflow.REGISTRY)}, None, "application/json"

    if method == "GET" and parts == ["api", "workflows"]:
        return 200, {"workflows": [w.to_dict() for w in workflow.REGISTRY.values()]}, None, "application/json"

    if method == "POST" and parts == ["api", "sessions"]:
        workflow_id = body.get("workflow_id")
        customer = body.get("customer")
        if not workflow_id or not customer:
            raise ApiError(400, "workflow_id and customer are required")
        try:
            session_id = sess.create(conn, workflow_id, customer)
        except workflow.WorkflowError as err:
            raise ApiError(400, str(err))
        return 201, {"session_id": session_id, "state": sess.CREATED}, None, "application/json"

    if len(parts) >= 3 and parts[0] == "api" and parts[1] == "sessions":
        session_id = parts[2]
        try:
            current = sess.get(conn, session_id)
        except sess.LifecycleError as err:
            raise ApiError(404, str(err))
        tail = parts[3:]

        if method == "GET" and not tail:
            return 200, _view(conn, session_id, current), None, "application/json"

        if method == "GET" and len(tail) == 2 and tail[0] == "documents":
            try:
                doc = documents.get_document(conn, tail[1])
            except documents.DocumentError as err:
                raise ApiError(404, str(err))
            if doc["session_id"] != session_id:
                raise ApiError(404, "no such document in this session")
            return 200, None, Path(doc["path"]).read_bytes(), "application/pdf"

        if method != "POST":
            raise ApiError(405, f"{method} not allowed here")

        try:
            if tail == ["document"]:
                filename = body.get("filename")
                content = body.get("content_base64")
                if not filename or not content:
                    raise ApiError(400, "filename and content_base64 are required")
                try:
                    decoded = base64.b64decode(content, validate=True)
                except Exception:
                    raise ApiError(400, "content_base64 is not valid base64")
                state, document_id = engine.intake(
                    conn, session_id, filename, decoded,
                    known_values=body.get("known_values"), root=data_root)
                return 200, {"state": state, "document_id": document_id,
                             "fields": sess.fields(conn, session_id)}, None, "application/json"

            if tail == ["price"]:
                sess.lock_price(conn, session_id, body.get("price_cents"), body.get("scope", ""))
                return 200, {"state": engine.evaluate(conn, session_id)}, None, "application/json"

            if tail == ["information"]:
                state = engine.supply(conn, session_id, body.get("field"), body.get("value"),
                                      body.get("supplied_by", current["customer"]))
                return 200, {"state": state, "fields": sess.fields(conn, session_id)}, None, "application/json"

            if tail == ["waive"]:
                state = engine.waive(conn, session_id, body.get("field"),
                                     body.get("waived_by", current["customer"]))
                return 200, {"state": state}, None, "application/json"

            if tail == ["execute"]:
                result = engine.execute(conn, session_id, root=data_root)
                return 200, {"result": result, "state": sess.get(conn, session_id)["state"]}, None, "application/json"

            if tail == ["approval"]:
                action = body.get("action")
                digest = body.get("payload_hash")
                decision = body.get("decision")
                if not action or not digest or not decision:
                    raise ApiError(400, "action, payload_hash and decision are required")
                trust_gate.decide(conn, session_id, action, digest, decision,
                                  body.get("decided_by", current["customer"]))
                return 200, {"recorded": decision,
                             "state": sess.get(conn, session_id)["state"]}, None, "application/json"

            if tail == ["finalise"]:
                result = engine.finalise(conn, session_id)
                return 200, {"result": result, "state": sess.get(conn, session_id)["state"]}, None, "application/json"

            if tail == ["cancel"]:
                state = engine.cancel(conn, session_id, body.get("by", current["customer"]))
                return 200, {"state": state}, None, "application/json"

        except (engine.NotPermitted, sess.LifecycleError, documents.DocumentError,
                workflow.WorkflowError) as err:
            raise ApiError(409, str(err))
        except ValueError as err:
            raise ApiError(400, str(err))

    raise ApiError(404, f"no route for {method} {path}")


def _view(conn, session_id, current):
    return {
        "session": {k: current[k] for k in ("id", "workflow_id", "customer", "state", "outcome",
                                            "failure_reason", "price_cents", "price_scope")},
        "fields": sess.fields(conn, session_id),
        "documents": [{k: d[k] for k in ("id", "role", "filename", "sha256", "byte_length", "attestation")}
                      for d in documents.documents_for(conn, session_id)],
        "pending_approval": trust_gate.pending(conn, session_id),
        "audit_trail": sess.trail(conn, session_id),
    }


def serve(host="127.0.0.1", port=8799, data_root=None, token=None):
    """Starts the real server. Returns (httpd, thread) so a caller can
    shut it down; running as a script blocks instead."""
    token = token or os.environ.get(config.API_TOKEN_ENV_VAR)
    if config.REQUIRE_AUTH and not token:
        raise RuntimeError(
            f"{config.API_TOKEN_ENV_VAR} is not set and REQUIRE_AUTH is on — refusing to serve an open API")
    httpd = ThreadingHTTPServer((host, port), _handler_class(data_root, token))
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd, thread


if __name__ == "__main__":
    server, _ = serve()
    print(f"Hands API on http://{server.server_address[0]}:{server.server_address[1]}")
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        server.shutdown()
