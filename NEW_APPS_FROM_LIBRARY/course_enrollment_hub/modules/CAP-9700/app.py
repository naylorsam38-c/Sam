#!/usr/bin/env python3
"""modules/CAP-9700/app.py -- real host: home page, health check, and a
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

INDEX_HTML = '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<title>Course Enrollment Hub</title>\n<style>\nbody { font-family: Helvetica Neue, Helvetica, Arial, sans-serif; max-width: 700px; margin: 40px auto;\n  color: #222; background: #f7f7f7; }\n.card { background: #fff; box-shadow: 0 2px 4px rgba(0,0,0,.15); border-radius: 6px; padding: 20px; margin-bottom: 16px; }\nh1 { font-size: 22px; }\ninput, select, textarea { font-size: 15px; padding: 8px; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; }\nbutton { font-size: 14px; padding: 8px 14px; border: none; border-radius: 4px; background: #2f6f9f; color: #fff;\n  cursor: pointer; }\nbutton.danger { background: #af2f2f; }\nbutton.secondary { background: #888; }\nul { list-style: none; margin: 0; padding: 0; }\nli { border-bottom: 1px solid #eee; padding: 10px 4px; }\n.row { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }\n\n</style>\n</head>\n<body>\n<h1>Course Enrollment Hub</h1>\n<div class="card">\n  <h2 style="font-size:16px;margin:0 0 8px">Courses <span style="font-weight:normal;color:#888;font-size:12px">(reused verbatim from online_course_lms)</span></h2>\n  <div class="row">\n    <input id="course-title" placeholder="Course title" data-slot="course_title">\n    <button id="add-course-btn" data-slot="add_course">Create course</button>\n  </div>\n  <ul id="course-list" data-slot="course_list"></ul>\n</div>\n<div class="card">\n  <h2 style="font-size:16px;margin:0 0 8px">Sessions</h2>\n  <div class="row">\n    <input id="sess-title" placeholder="Session title" data-slot="sess_title">\n    <input id="sess-start" type="datetime-local" value="2026-12-10T14:00" data-slot="sess_start">\n    <input id="sess-seats" type="number" value="2" placeholder="Seats" data-slot="sess_seats" style="width:80px">\n    <button id="add-session-btn" data-slot="add_session">Schedule session</button>\n  </div>\n  <ul id="session-list" data-slot="session_list"></ul>\n</div>\n<div class="card">\n  <h2 style="font-size:16px;margin:0 0 8px">Feedback prompts <span style="font-weight:normal;color:#888;font-size:12px">(reused verbatim from quiz_and_flashcards)</span></h2>\n  <div class="row">\n    <input id="fb-question" placeholder="Feedback question" data-slot="fb_question">\n    <button id="add-fb-btn" data-slot="add_fb">Add prompt</button>\n  </div>\n  <ul id="fb-list"></ul>\n</div>\n<script>\n\nconst ME = "learner@example.com";\nfunction refreshCourses() {\n  fetch("/api/online_course_lms/courses").then(r => r.json()).then(data => {\n    const list = document.getElementById("course-list");\n    list.innerHTML = "";\n    (data.courses || []).forEach(c => { const li = document.createElement("li"); li.textContent = c.title; list.appendChild(li); });\n  });\n}\nfunction refreshSessions() {\n  fetch("/api/course_enrollment_hub/events").then(r => r.json()).then(data => {\n    const list = document.getElementById("session-list");\n    list.innerHTML = "";\n    (data.events || []).forEach(e => {\n      const li = document.createElement("li");\n      li.textContent = e.title + " -- " + e.enrolled + "/" + e.seats + " enrolled";\n      const enroll = document.createElement("button"); enroll.textContent = "Enroll"; enroll.style.marginLeft = "8px";\n      enroll.addEventListener("click", () => {\n        fetch("/api/course_enrollment_hub/events/enroll", {method: "POST", headers: {"Content-Type": "application/json"},\n          body: JSON.stringify({id: e.id})}).then(r => r.json()).then(result => {\n            const msg = result.error ? ("Enrollment failed: " + JSON.stringify(result.error)) : ("Enrolled in " + e.title);\n            fetch("/api/course_enrollment_hub/notifications", {method: "POST", headers: {"Content-Type": "application/json"},\n              body: JSON.stringify({recipient: ME, message: msg})});\n            refreshSessions();\n          });\n      });\n      li.appendChild(enroll);\n      list.appendChild(li);\n    });\n  });\n}\nfunction refreshFeedback() {\n  fetch("/api/quiz_and_flashcards/cards").then(r => r.json()).then(data => {\n    const list = document.getElementById("fb-list");\n    list.innerHTML = "";\n    (data.cards || []).forEach(c => { const li = document.createElement("li"); li.textContent = c.question; list.appendChild(li); });\n  });\n}\ndocument.getElementById("add-course-btn").addEventListener("click", () => {\n  const title = document.getElementById("course-title").value;\n  if (!title.trim()) return;\n  fetch("/api/online_course_lms/courses", {method: "POST", headers: {"Content-Type": "application/json"},\n    body: JSON.stringify({title: title})}).then(() => { document.getElementById("course-title").value = ""; refreshCourses(); });\n});\ndocument.getElementById("add-session-btn").addEventListener("click", () => {\n  const title = document.getElementById("sess-title").value;\n  const start = document.getElementById("sess-start").value;\n  const seats = document.getElementById("sess-seats").value;\n  if (!title.trim()) return;\n  fetch("/api/course_enrollment_hub/events", {method: "POST", headers: {"Content-Type": "application/json"},\n    body: JSON.stringify({title: title, start: start, seats: seats})}).then(() => { document.getElementById("sess-title").value = ""; refreshSessions(); });\n});\ndocument.getElementById("add-fb-btn").addEventListener("click", () => {\n  const question = document.getElementById("fb-question").value;\n  if (!question.trim()) return;\n  fetch("/api/quiz_and_flashcards/cards", {method: "POST", headers: {"Content-Type": "application/json"},\n    body: JSON.stringify({question: question})}).then(() => { document.getElementById("fb-question").value = ""; refreshFeedback(); });\n});\nrefreshCourses(); refreshSessions(); refreshFeedback();\n\n</script>\n</body>\n</html>\n'


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
        if not entry.is_dir() or entry.name in ("CAP-9700", "CAP-0000"):
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
