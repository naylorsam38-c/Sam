#!/usr/bin/env python3
"""modules/CAP-0100/app.py -- real host: home page, health check, and a
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

INDEX_HTML = '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<title>Todos</title>\n<style>\nbody { font-family: Helvetica Neue, Helvetica, Arial, sans-serif; max-width: 550px; margin: 40px auto; }\n.todoapp { background: #fff; box-shadow: 0 2px 4px rgba(0,0,0,.2); }\n.header input#new-todo { width: 100%; box-sizing: border-box; font-size: 20px; padding: 12px; border: none;\n  border-bottom: 1px solid #ededed; }\nul#todo-list { list-style: none; margin: 0; padding: 0; }\nul#todo-list li { position: relative; border-bottom: 1px solid #ededed; padding: 12px 12px 12px 40px; }\nul#todo-list li .toggle { position: absolute; left: 10px; top: 14px; }\nul#todo-list li label { margin-left: 6px; }\nul#todo-list li.completed label { text-decoration: line-through; color: #949494; }\nul#todo-list li .destroy { display: none; float: right; cursor: pointer; border: none; background: none; }\nul#todo-list li:hover .destroy { display: inline; }\nul#todo-list li .edit { display: none; width: 90%; font-size: 16px; }\nul#todo-list li.editing .edit { display: inline; }\nul#todo-list li.editing .view { display: none; }\n.footer { padding: 10px 15px; display: flex; justify-content: space-between; align-items: center; }\n.footer .filters { list-style: none; display: inline-flex; gap: 8px; margin: 0; padding: 0; }\n.footer .filters a { text-decoration: none; color: #777; padding: 2px 6px; border: 1px solid transparent; }\n.footer .filters a.selected { border-color: rgba(175,47,47,.2); border-radius: 3px; }\n#clear-completed { border: none; background: none; cursor: pointer; color: #777; }\n</style>\n</head>\n<body>\n<section class="todoapp">\n  <header class="header">\n    <input id="new-todo" data-slot="new_todo" placeholder="What needs to be done?" autofocus>\n  </header>\n  <section class="main">\n    <input id="toggle-all" data-slot="toggle_all" type="checkbox">\n    <label for="toggle-all">Mark all as complete</label>\n    <ul id="todo-list" data-slot="todo_list"></ul>\n  </section>\n  <footer class="footer">\n    <span id="todo-count"></span>\n    <ul class="filters">\n      <li><a href="#/" data-filter="all">All</a></li>\n      <li><a href="#/active" data-filter="active">Active</a></li>\n      <li><a href="#/completed" data-filter="completed">Completed</a></li>\n    </ul>\n    <button id="clear-completed" data-slot="clear_completed">Clear completed</button>\n  </footer>\n</section>\n<script>\nvar todos = [];\nvar editingId = null;\n\nfunction currentFilter() {\n  var h = location.hash;\n  if (h === "#/active") return "active";\n  if (h === "#/completed" || h === "#!/") return "completed";\n  return "all";\n}\n\nfunction refresh() {\n  fetch("/api/todos").then(function(r) { return r.json(); }).then(function(data) {\n    todos = data.todos || [];\n    render();\n  });\n}\n\nfunction render() {\n  var filter = currentFilter();\n  var list = document.getElementById("todo-list");\n  list.innerHTML = "";\n  todos.forEach(function(t) {\n    if (filter === "active" && t.completed) return;\n    if (filter === "completed" && !t.completed) return;\n    var li = document.createElement("li");\n    li.className = (t.completed ? "completed " : "") + (editingId === t.id ? "editing" : "");\n    li.dataset.id = t.id;\n\n    var view = document.createElement("div");\n    view.className = "view";\n    var toggle = document.createElement("input");\n    toggle.type = "checkbox"; toggle.className = "toggle"; toggle.checked = !!t.completed;\n    toggle.addEventListener("change", function() { toggleTodo(t.id); });\n    var label = document.createElement("label");\n    label.textContent = t.title;\n    label.addEventListener("dblclick", function() { startEdit(t.id); });\n    var destroy = document.createElement("button");\n    destroy.className = "destroy"; destroy.textContent = "x";\n    destroy.addEventListener("click", function() { deleteTodo(t.id); });\n    view.appendChild(toggle); view.appendChild(label); view.appendChild(destroy);\n\n    var editInput = document.createElement("input");\n    editInput.className = "edit"; editInput.value = t.title;\n    editInput.addEventListener("keydown", function(e) {\n      if (e.key === "Enter") editInput.blur();\n      if (e.key === "Escape") { editingId = null; render(); }\n    });\n    editInput.addEventListener("blur", function() { saveEdit(t.id, editInput.value); });\n\n    li.appendChild(view); li.appendChild(editInput);\n    list.appendChild(li);\n    if (editingId === t.id) { editInput.focus(); }\n  });\n\n  var activeCount = todos.filter(function(t) { return !t.completed; }).length;\n  var word = activeCount === 1 ? "item" : "items";\n  document.getElementById("todo-count").innerHTML = "<strong>" + activeCount + "</strong> " + word + " left";\n\n  var completedCount = todos.filter(function(t) { return t.completed; }).length;\n  document.getElementById("clear-completed").style.display = completedCount > 0 ? "inline" : "none";\n\n  document.querySelectorAll(".filters a").forEach(function(a) {\n    a.className = a.dataset.filter === filter ? "selected" : "";\n  });\n\n  document.getElementById("toggle-all").checked = todos.length > 0 && activeCount === 0;\n}\n\nfunction addTodo(title) {\n  title = title.trim();\n  if (!title) return;\n  fetch("/api/todos", {\n    method: "POST", headers: {"Content-Type": "application/json"},\n    body: JSON.stringify({title: title})\n  }).then(refresh);\n}\n\nfunction toggleTodo(id) {\n  fetch("/api/todos/toggle", {\n    method: "POST", headers: {"Content-Type": "application/json"},\n    body: JSON.stringify({id: id})\n  }).then(refresh);\n}\n\nfunction deleteTodo(id) {\n  fetch("/api/todos/delete", {\n    method: "POST", headers: {"Content-Type": "application/json"},\n    body: JSON.stringify({id: id})\n  }).then(refresh);\n}\n\nfunction startEdit(id) { editingId = id; render(); }\n\nfunction saveEdit(id, title) {\n  if (editingId !== id) return;\n  editingId = null;\n  title = title.trim();\n  if (!title) { deleteTodo(id); return; }\n  fetch("/api/todos/edit", {\n    method: "POST", headers: {"Content-Type": "application/json"},\n    body: JSON.stringify({id: id, title: title})\n  }).then(refresh);\n}\n\nfunction toggleAll(completed) {\n  fetch("/api/todos/toggle_all", {\n    method: "POST", headers: {"Content-Type": "application/json"},\n    body: JSON.stringify({completed: completed})\n  }).then(refresh);\n}\n\nfunction clearCompleted() {\n  fetch("/api/todos/clear_completed", {method: "POST"}).then(refresh);\n}\n\ndocument.getElementById("new-todo").addEventListener("keydown", function(e) {\n  if (e.key === "Enter") { addTodo(e.target.value); e.target.value = ""; }\n});\ndocument.getElementById("toggle-all").addEventListener("change", function(e) {\n  toggleAll(e.target.checked);\n});\ndocument.getElementById("clear-completed").addEventListener("click", clearCompleted);\nwindow.addEventListener("hashchange", render);\n\nrefresh();\n</script>\n</body>\n</html>\n'


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
        if not entry.is_dir() or entry.name in ("CAP-0100", "CAP-0000"):
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
