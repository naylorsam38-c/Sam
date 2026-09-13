#!/usr/bin/env python3
"""modules/CAP-0200/app.py -- real host: home page, health check, and a
dynamic loader for sibling capability modules (modules/<CAP-id>/route.py) --
the same proven convention as CAP-0001's fixture host and the round-7 real
todo app's CAP-0100 host. Now also the one place that normalizes every
capability's error response into the Common Capability Contract's standard
shape and passes a standard identity/context object to any handler that
declares it wants one -- both done centrally here, so upgrading either
never required touching a single capability's own handler code."""
import argparse
import importlib.util
import inspect
import logging
import sys
from pathlib import Path
from flask import Flask, jsonify, request, Response

app = Flask(__name__)
HERE = Path(__file__).resolve().parent
MODULES_ROOT = HERE.parent

# Real server-side diagnostic logging, deliberately stdout-based -- the
# standard idiom a log-shipping agent (CloudWatch, an ECS awslogs driver, a
# systemd journal) already knows how to pick up with no application-level
# credential or SDK call. Deliberately logs no request body and no header
# anywhere in this file -- nothing sensitive (a password, a token) is ever
# captured in the first place, so there is nothing here that needs
# field-level redaction.
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
_diagnostic_log = logging.getLogger("pilot.host")

_shared_lib_path = MODULES_ROOT / "CAP-0000" / "shared_lib.py"
_spec = importlib.util.spec_from_file_location("cap0000_shared_lib", _shared_lib_path)
_shared = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_shared)

INDEX_HTML = '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<title>Notes</title>\n<style>\nbody { font-family: Helvetica Neue, Helvetica, Arial, sans-serif; max-width: 700px; margin: 40px auto;\n  color: #222; background: #f7f7f7; }\n.card { background: #fff; box-shadow: 0 2px 4px rgba(0,0,0,.15); border-radius: 6px; padding: 20px; margin-bottom: 16px; }\nh1 { font-size: 22px; }\ninput, select, textarea { font-size: 15px; padding: 8px; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; }\nbutton { font-size: 14px; padding: 8px 14px; border: none; border-radius: 4px; background: #2f6f9f; color: #fff;\n  cursor: pointer; }\nbutton.danger { background: #af2f2f; }\nbutton.secondary { background: #888; }\nul { list-style: none; margin: 0; padding: 0; }\nli { border-bottom: 1px solid #eee; padding: 10px 4px; }\n.row { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }\n\n</style>\n</head>\n<body>\n<h1>Notes</h1>\n<div class="card" id="login-card">\n  <h2 style="font-size:16px;margin:0 0 8px">Log in</h2>\n  <div class="row" id="login-fields">\n    <input id="login-email" placeholder="Email" data-slot="login_email">\n    <input id="login-password" type="password" placeholder="Password" data-slot="login_password">\n    <button id="login-btn" data-slot="login">Log in</button>\n  </div>\n  <button id="logout-btn" data-slot="logout" class="secondary" style="display:none">Log out</button>\n  <div id="login-result"></div>\n</div>\n<div class="card" id="notes-card" style="display:none">\n  <div class="row">\n    <input id="note-title" placeholder="Title" data-slot="note_title">\n    <textarea id="note-body" placeholder="Write your note..." data-slot="note_body" rows="3" style="flex:1"></textarea>\n    <button id="add-note-btn" data-slot="add_note">Add note</button>\n  </div>\n</div>\n<div class="card" id="notes-list-card" style="display:none">\n  <ul id="note-list" data-slot="note_list"></ul>\n</div>\n<div class="card">\n  <h2 style="font-size:16px;margin:0 0 8px">Admin setup (first run only)</h2>\n  <div class="row">\n    <input id="bootstrap-email" placeholder="Admin email" data-slot="bootstrap_email">\n    <input id="bootstrap-password" type="password" placeholder="Password (min 8 chars)" value="correcthorse" data-slot="bootstrap_password">\n    <button id="bootstrap-btn" data-slot="bootstrap_admin">Create first admin account</button>\n  </div>\n  <div id="bootstrap-result"></div>\n</div>\n<script>\n\nlet authToken = null;\n\nfunction showLoggedIn(email) {\n  document.getElementById("login-fields").style.display = "none";\n  document.getElementById("logout-btn").style.display = "inline-block";\n  document.getElementById("login-result").textContent = "Logged in as " + email;\n  document.getElementById("notes-card").style.display = "block";\n  document.getElementById("notes-list-card").style.display = "block";\n  refresh();\n}\n\nfunction showLoggedOut() {\n  authToken = null;\n  document.getElementById("login-fields").style.display = "flex";\n  document.getElementById("logout-btn").style.display = "none";\n  document.getElementById("login-result").textContent = "";\n  document.getElementById("notes-card").style.display = "none";\n  document.getElementById("notes-list-card").style.display = "none";\n  document.getElementById("note-list").innerHTML = "";\n}\n\ndocument.getElementById("login-btn").addEventListener("click", () => {\n  const email = document.getElementById("login-email").value;\n  const password = document.getElementById("login-password").value;\n  fetch("/api/note_taking/auth/login", {method: "POST", headers: {"Content-Type": "application/json"},\n    body: JSON.stringify({email: email, password: password})})\n    .then(r => r.json().then(data => ({status: r.status, data: data})))\n    .then(res => {\n      if (res.status === 200) {\n        authToken = res.data.token;\n        showLoggedIn(email);\n      } else {\n        document.getElementById("login-result").textContent = "Login failed";\n      }\n    });\n});\n\ndocument.getElementById("logout-btn").addEventListener("click", () => {\n  fetch("/api/note_taking/auth/logout", {method: "POST",\n    headers: {"Authorization": "Bearer " + authToken}}).then(showLoggedOut);\n});\n\ndocument.getElementById("bootstrap-btn").addEventListener("click", () => {\n  const email = document.getElementById("bootstrap-email").value;\n  const password = document.getElementById("bootstrap-password").value;\n  if (!email.trim()) return;\n  fetch("/api/note_taking/auth/bootstrap-admin", {method: "POST", headers: {"Content-Type": "application/json"},\n    body: JSON.stringify({email: email, password: password})})\n    .then(r => r.json().then(data => ({status: r.status, data: data})))\n    .then(res => {\n      const resultEl = document.getElementById("bootstrap-result");\n      if (res.status === 201) {\n        resultEl.textContent = "Admin created: " + res.data.email;\n      } else {\n        const msg = (res.data.error && res.data.error.message) || JSON.stringify(res.data);\n        resultEl.textContent = "Bootstrap failed: " + msg;\n      }\n    });\n});\n\nfunction refresh() {\n  if (!authToken) return;\n  fetch("/api/note_taking/notes", {headers: {"Authorization": "Bearer " + authToken}}).then(r => r.json()).then(data => {\n    const list = document.getElementById("note-list");\n    list.innerHTML = "";\n    (data.notes || []).forEach(n => {\n      const li = document.createElement("li");\n      li.dataset.id = n.id;\n      const strong = document.createElement("strong");\n      strong.textContent = n.title;\n      const p = document.createElement("div");\n      p.textContent = n.body;\n      const del = document.createElement("button");\n      del.className = "danger"; del.textContent = "Delete";\n      del.addEventListener("click", () => {\n        fetch("/api/note_taking/notes/delete", {method: "POST",\n          headers: {"Content-Type": "application/json", "Authorization": "Bearer " + authToken},\n          body: JSON.stringify({id: n.id})}).then(refresh);\n      });\n      li.appendChild(strong); li.appendChild(p); li.appendChild(del);\n      list.appendChild(li);\n    });\n  });\n}\ndocument.getElementById("add-note-btn").addEventListener("click", () => {\n  const title = document.getElementById("note-title").value;\n  const body = document.getElementById("note-body").value;\n  if (!title.trim()) return;\n  fetch("/api/note_taking/notes", {method: "POST",\n    headers: {"Content-Type": "application/json", "Authorization": "Bearer " + authToken},\n    body: JSON.stringify({title: title, body: body})}).then(() => {\n      document.getElementById("note-title").value = "";\n      document.getElementById("note-body").value = "";\n      refresh();\n    });\n});\n\n</script>\n</body>\n</html>\n'


@app.route("/health")
def health():
    return jsonify({"ok": True}), 200


@app.route("/")
def index():
    return Response(INDEX_HTML, mimetype="text/html")


ROUTE_HANDLERS = {}
HANDLER_WANTS_CTX = {}


def load_modules():
    if not MODULES_ROOT.is_dir():
        return
    for entry in sorted(MODULES_ROOT.iterdir()):
        if not entry.is_dir() or entry.name in ("CAP-0200", "CAP-0000"):
            continue
        route_file = entry / "route.py"
        if not route_file.is_file():
            continue
        spec = importlib.util.spec_from_file_location(f"mod_{entry.name}", route_file)
        mod = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(mod)
        except Exception as e:
            print(f"module {entry.name} failed to load: {e}")
            continue
        route = getattr(mod, "ROUTE", None)
        method = getattr(mod, "METHOD", "GET")
        handler = getattr(mod, "handle", None)
        if route and handler:
            key = (method, route)
            ROUTE_HANDLERS[key] = handler
            # Standard identity/context passing: a handler that declares a
            # second parameter gets a real ctx object (see _make_ctx()) --
            # real session/role/service-key resolution, not a placeholder.
            # A handler that doesn't declare it is called exactly as before.
            HANDLER_WANTS_CTX[key] = len(inspect.signature(handler).parameters) >= 2


load_modules()


def _make_ctx(request):
    """Real identity resolution, not a stub: a Bearer token in the real
    Authorization header is checked against a real, server-side session
    (expiry genuinely enforced -- see CAP-0000's validate_session()); an
    X-API-Key header is checked against a real, hashed service credential.
    Neither is trusted from client-supplied user/role fields in the request
    body -- ctx["user"]/ctx["role"] only ever come from what the server's
    own session store says, and the raw token is carried through so a
    capability like logout can invalidate the exact session that made the
    request."""
    token = None
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
    session = _shared.validate_session(token) if token else None
    api_key_header = request.headers.get("X-API-Key")
    api_key_record = _shared.validate_api_key(api_key_header) if api_key_header else None
    ctx = {"user": None, "authenticated": False, "role": None, "token": token, "service": None}
    if session:
        ctx["user"] = session.get("user_id")
        ctx["authenticated"] = True
        ctx["role"] = session.get("role")
    if api_key_record:
        ctx["service"] = api_key_record.get("service_name")
        ctx["authenticated"] = True
    return ctx


def _error_body(status, message):
    return {"error": {"code": _shared.code_for_status(status), "message": message}}


@app.route("/<path:subpath>", methods=["GET", "POST"])
def dispatch(subpath):
    path = "/" + subpath
    key = (request.method, path)
    handler = ROUTE_HANDLERS.get(key)
    if handler is None:
        return jsonify(_error_body(404, "not found")), 404
    try:
        if HANDLER_WANTS_CTX.get(key):
            status, body = handler(request, _make_ctx(request))
        else:
            status, body = handler(request)
    except Exception as e:
        # Real fix (PRIVATE_PILOT_SAFETY_MILESTONE.md item 4): the exception
        # detail goes to the server-side log only, never to the client --
        # closing a genuine information-disclosure gap this project's own
        # planning documents found (a caught exception's message used to be
        # echoed straight back in the HTTP response body). Deliberately
        # logs only method/path/exception type/message -- never the request
        # body or headers, so no credential this app might one day handle
        # can ever reach this log line to begin with.
        _diagnostic_log.exception("handler error  %s %s  %s", request.method, path, type(e).__name__)
        return jsonify(_error_body(500, "internal error")), 500
    # Real binary responses (CAP-0000's save_blob()/load_blob(), the real
    # document-storage primitive): a handler that wants to serve raw bytes
    # with a real Content-Type returns {"__binary__": True, "data": <bytes>,
    # "content_type": <str>} instead of a plain JSON-able dict. Checked by
    # a sentinel key no pre-existing handler_body ever returns, so every
    # handler predating this stays on the jsonify() path unchanged.
    if isinstance(body, dict) and body.get("__binary__"):
        return Response(body["data"], mimetype=body.get("content_type", "application/octet-stream"), status=status)
    # Standard error shape: any handler that still returns the older bare
    # {"error": "<string>"} shape (every handler_body string predating this
    # contract) gets it normalized here, once, centrally -- so the wire
    # contract is uniform without having rewritten 187 handler bodies.
    if status >= 400 and isinstance(body, dict) and isinstance(body.get("error"), str):
        body = _error_body(status, body["error"])
    return jsonify(body), status


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=5000)
    args = parser.parse_args()
    app.run(host="127.0.0.1", port=args.port)
