#!/usr/bin/env python3
"""modules/CAP-0900/app.py -- real host: home page, health check, and a
dynamic loader for sibling capability modules (modules/<CAP-id>/route.py) --
the same proven convention as CAP-0001's fixture host and the round-7 real
todo app's CAP-0100 host."""
import argparse
import importlib.util
from pathlib import Path
from flask import Flask, jsonify, request, Response

app = Flask(__name__)
HERE = Path(__file__).resolve().parent
MODULES_ROOT = HERE.parent

INDEX_HTML = '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<title>Helpdesk</title>\n<style>\nbody { font-family: Helvetica Neue, Helvetica, Arial, sans-serif; max-width: 700px; margin: 40px auto;\n  color: #222; background: #f7f7f7; }\n.card { background: #fff; box-shadow: 0 2px 4px rgba(0,0,0,.15); border-radius: 6px; padding: 20px; margin-bottom: 16px; }\nh1 { font-size: 22px; }\ninput, select, textarea { font-size: 15px; padding: 8px; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; }\nbutton { font-size: 14px; padding: 8px 14px; border: none; border-radius: 4px; background: #2f6f9f; color: #fff;\n  cursor: pointer; }\nbutton.danger { background: #af2f2f; }\nbutton.secondary { background: #888; }\nul { list-style: none; margin: 0; padding: 0; }\nli { border-bottom: 1px solid #eee; padding: 10px 4px; }\n.row { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }\n\n</style>\n</head>\n<body>\n<h1>Helpdesk</h1>\n<div class="card">\n  <div class="row">\n    <input id="t-subject" placeholder="Ticket subject" data-slot="t_subject">\n    <button id="add-ticket-btn" data-slot="add_ticket">Create ticket</button>\n  </div>\n</div>\n<div class="card"><ul id="ticket-list" data-slot="ticket_list"></ul></div>\n<script>\n\nfunction refresh() {\n  fetch("/api/tickets").then(r => r.json()).then(data => {\n    const list = document.getElementById("ticket-list");\n    list.innerHTML = "";\n    (data.tickets || []).forEach(t => {\n      const li = document.createElement("li");\n      li.textContent = t.subject + " (" + t.status + ")";\n      if (t.status === "open") {\n        const close = document.createElement("button");\n        close.textContent = "Close"; close.style.marginLeft = "8px";\n        close.addEventListener("click", () => {\n          fetch("/api/tickets/close", {method: "POST", headers: {"Content-Type": "application/json"},\n            body: JSON.stringify({id: t.id})}).then(refresh);\n        });\n        li.appendChild(close);\n      }\n      list.appendChild(li);\n    });\n  });\n}\ndocument.getElementById("add-ticket-btn").addEventListener("click", () => {\n  const subject = document.getElementById("t-subject").value;\n  if (!subject.trim()) return;\n  fetch("/api/tickets", {method: "POST", headers: {"Content-Type": "application/json"},\n    body: JSON.stringify({subject: subject})}).then(() => {\n      document.getElementById("t-subject").value = "";\n      refresh();\n    });\n});\nrefresh();\n\n</script>\n</body>\n</html>\n'


@app.route("/health")
def health():
    return jsonify({"ok": True}), 200


@app.route("/")
def index():
    return Response(INDEX_HTML, mimetype="text/html")


ROUTE_HANDLERS = {}


def load_modules():
    if not MODULES_ROOT.is_dir():
        return
    for entry in sorted(MODULES_ROOT.iterdir()):
        if not entry.is_dir() or entry.name == "CAP-0900":
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
            ROUTE_HANDLERS[(method, route)] = handler


load_modules()


@app.route("/<path:subpath>", methods=["GET", "POST"])
def dispatch(subpath):
    path = "/" + subpath
    handler = ROUTE_HANDLERS.get((request.method, path))
    if handler is None:
        return jsonify({"error": "not found"}), 404
    try:
        status, body = handler(request)
    except Exception as e:
        return jsonify({"error": f"handler raised {type(e).__name__}: {e}"}), 500
    return jsonify(body), status


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=5000)
    args = parser.parse_args()
    app.run(host="127.0.0.1", port=args.port)
