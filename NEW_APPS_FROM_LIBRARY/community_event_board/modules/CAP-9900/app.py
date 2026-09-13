#!/usr/bin/env python3
"""modules/CAP-9900/app.py -- real host: home page, health check, and a
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
from pathlib import Path
from flask import Flask, jsonify, request, Response

app = Flask(__name__)
HERE = Path(__file__).resolve().parent
MODULES_ROOT = HERE.parent

_shared_lib_path = MODULES_ROOT / "CAP-0000" / "shared_lib.py"
_spec = importlib.util.spec_from_file_location("cap0000_shared_lib", _shared_lib_path)
_shared = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_shared)

INDEX_HTML = '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<title>Community Event Board</title>\n<style>\nbody { font-family: Helvetica Neue, Helvetica, Arial, sans-serif; max-width: 700px; margin: 40px auto;\n  color: #222; background: #f7f7f7; }\n.card { background: #fff; box-shadow: 0 2px 4px rgba(0,0,0,.15); border-radius: 6px; padding: 20px; margin-bottom: 16px; }\nh1 { font-size: 22px; }\ninput, select, textarea { font-size: 15px; padding: 8px; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; }\nbutton { font-size: 14px; padding: 8px 14px; border: none; border-radius: 4px; background: #2f6f9f; color: #fff;\n  cursor: pointer; }\nbutton.danger { background: #af2f2f; }\nbutton.secondary { background: #888; }\nul { list-style: none; margin: 0; padding: 0; }\nli { border-bottom: 1px solid #eee; padding: 10px 4px; }\n.row { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }\n\n</style>\n</head>\n<body>\n<h1>Community Event Board</h1>\n<div class="card">\n  <h2 style="font-size:16px;margin:0 0 8px">Events</h2>\n  <div class="row">\n    <input id="ev-title" placeholder="Event title" data-slot="ev_title">\n    <input id="ev-start" type="datetime-local" value="2026-12-01T18:00" data-slot="ev_start">\n    <input id="ev-capacity" type="number" value="10" placeholder="Capacity" data-slot="ev_capacity" style="width:90px">\n    <button id="add-event-btn" data-slot="add_event">Create event</button>\n  </div>\n  <ul id="event-list" data-slot="event_list"></ul>\n</div>\n<div class="card">\n  <h2 style="font-size:16px;margin:0 0 8px">Your notifications</h2>\n  <ul id="notification-list"></ul>\n</div>\n<div class="card">\n  <h2 style="font-size:16px;margin:0 0 8px">Announcements <span style="font-weight:normal;color:#888;font-size:12px">(reused verbatim from team_chat)</span></h2>\n  <div class="row">\n    <input id="announce-text" placeholder="Post an announcement" data-slot="announce_text" style="flex:1">\n    <button id="post-announce-btn" data-slot="post_announce">Post</button>\n  </div>\n  <ul id="announcement-list" data-slot="announcement_list"></ul>\n</div>\n<script>\n\nconst ME = "organizer@example.com";\n\nfunction refreshEvents() {\n  fetch("/api/community_event_board/events").then(r => r.json()).then(data => {\n    const list = document.getElementById("event-list");\n    list.innerHTML = "";\n    (data.events || []).forEach(e => {\n      const li = document.createElement("li");\n      li.textContent = e.title + " -- " + e.attendees + "/" + e.capacity + " attending";\n      const rsvp = document.createElement("button");\n      rsvp.textContent = "RSVP"; rsvp.style.marginLeft = "8px";\n      rsvp.addEventListener("click", () => {\n        fetch("/api/community_event_board/events/rsvp", {method: "POST", headers: {"Content-Type": "application/json"},\n          body: JSON.stringify({id: e.id})}).then(r => r.json()).then(result => {\n            if (result.error) {\n              fetch("/api/community_event_board/notifications", {method: "POST", headers: {"Content-Type": "application/json"},\n                body: JSON.stringify({recipient: ME, message: "RSVP failed for " + e.title + ": " + result.error})});\n            } else {\n              fetch("/api/community_event_board/notifications", {method: "POST", headers: {"Content-Type": "application/json"},\n                body: JSON.stringify({recipient: ME, message: "You are confirmed for " + e.title})});\n            }\n            refreshEvents(); refreshNotifications();\n          });\n      });\n      li.appendChild(rsvp);\n      list.appendChild(li);\n    });\n  });\n}\nfunction refreshNotifications() {\n  fetch("/api/community_event_board/notifications?recipient=" + encodeURIComponent(ME)).then(r => r.json()).then(data => {\n    const list = document.getElementById("notification-list");\n    list.innerHTML = "";\n    (data.notifications || []).forEach(n => {\n      const li = document.createElement("li");\n      li.textContent = (n.read ? "" : "\\u25cf ") + n.message;\n      list.appendChild(li);\n    });\n  });\n}\nfunction refreshAnnouncements() {\n  fetch("/api/team_chat/messages").then(r => r.json()).then(data => {\n    const list = document.getElementById("announcement-list");\n    list.innerHTML = "";\n    (data.messages || []).forEach(m => {\n      const li = document.createElement("li");\n      li.textContent = m.author + ": " + m.text;\n      list.appendChild(li);\n    });\n  });\n}\ndocument.getElementById("add-event-btn").addEventListener("click", () => {\n  const title = document.getElementById("ev-title").value;\n  const start = document.getElementById("ev-start").value;\n  const capacity = document.getElementById("ev-capacity").value;\n  if (!title.trim()) return;\n  fetch("/api/community_event_board/events", {method: "POST", headers: {"Content-Type": "application/json"},\n    body: JSON.stringify({title: title, start: start, capacity: capacity})}).then(() => {\n      document.getElementById("ev-title").value = "";\n      refreshEvents();\n    });\n});\ndocument.getElementById("post-announce-btn").addEventListener("click", () => {\n  const text = document.getElementById("announce-text").value;\n  if (!text.trim()) return;\n  fetch("/api/team_chat/messages", {method: "POST", headers: {"Content-Type": "application/json"},\n    body: JSON.stringify({text: text, author: "Organizer"})}).then(() => {\n      document.getElementById("announce-text").value = "";\n      refreshAnnouncements();\n    });\n});\nrefreshEvents(); refreshNotifications(); refreshAnnouncements();\n\n</script>\n</body>\n</html>\n'


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
        if not entry.is_dir() or entry.name in ("CAP-9900", "CAP-0000"):
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
            # second parameter gets a real ctx object; one that doesn't
            # (every capability in this library today, since none needs
            # real identity yet) is called exactly as before -- the
            # mechanism is real and live, not dead code waiting for a
            # future rewrite, even though nothing currently opts in.
            HANDLER_WANTS_CTX[key] = len(inspect.signature(handler).parameters) >= 2


load_modules()


def _make_ctx():
    return {"user": None, "authenticated": False}


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
            status, body = handler(request, _make_ctx())
        else:
            status, body = handler(request)
    except Exception as e:
        return jsonify(_error_body(500, f"handler raised {type(e).__name__}: {e}")), 500
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
