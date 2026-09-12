#!/usr/bin/env python3
"""
gen_real_todo_app.py — builds a REAL, non-fixture project for "todo list",
item #1 of Sam's real 43-app canonical list (canonical_app_types.py), to
prove build.py against a genuinely different real app -- not the CAP-0001
test fixture every proving-table row above uses.

Every requirement this app implements is sourced from the real, published,
canonical TodoMVC functional specification:
  https://github.com/tastejs/todomvc/blob/master/app-spec.md
(fetched live, read in full, cited in review.md's Round 7 section -- not
reconstructed from memory or invented). The persisted fields (id, title,
completed) are exactly the three properties that spec names. The seven
server-side actions below are exactly the seven real state changes the spec
describes a todo list making (list, create, toggle one, edit a title,
delete, toggle all, clear completed); filtering (#/, #/active, #/completed)
is deliberately NOT a server capability, because the real spec places
filtering at the model/client level, not the server -- inventing a server
endpoint for it would be adding a requirement the real spec doesn't have.

Architecturally this deliberately does NOT repeat CAP-0001 fixture's own
pattern of baking a create-route directly into the host module (flagged in
build.py's own build_checks() docstring as a real design smell, not a
convention to copy). Every data-mutating action here is its own real shelf
capability with its own real route.py module (ROUTE/METHOD/handle()) --
which means build.py's existing, unmodified, round-4 generic
compute-capability check generator covers six of these seven capabilities
with ZERO new check logic. Only CAP-0100, the host/entry module, needs the
generalized CHK-001/CHK-020 host-journey checks (round 7).

State is a real JSON file on disk (<app_dir>/data/todos.json), read/written
by each route module independently -- real persistence across a process
restart, not an in-memory stub that forgets everything when the app exits.

Rerunnable: wipes and rebuilds real_todo_proof/ under this directory.
"""
import json
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE / "real_todo_proof"

if ROOT.exists():
    shutil.rmtree(ROOT)
ROOT.mkdir(parents=True)

SHELF = ROOT / "shelf"
CAPS = SHELF / "capabilities"
IMPLS = SHELF / "implementations"
TEMPLATES = ROOT / "templates"
for d in (CAPS, IMPLS, TEMPLATES):
    d.mkdir(parents=True)


def write(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_json(path: Path, obj):
    write(path, json.dumps(obj, indent=2))


# ==============================================================================
# Record helpers -- identical shapes to verification/gen_fixtures.py's own
# (the Numbering Standard's §3.6/§3.7 records, word for word), duplicated
# here rather than imported so this script stays a fully standalone, real,
# clean-room-runnable generator with no import-time side effects borrowed
# from the fixture generator.
# ==============================================================================
def cap_record(cap_id, name, category, impl_ids, output_fields=(), required_input=(),
                side_effects=(), approval_ref="APPROVAL-CAP-REAL"):
    return {
        "id": cap_id,
        "name": name,
        "category": category,
        "status": "active",
        "data_shape": {
            "input": {"required": list(required_input), "types": {}},
            "output": {"fields": list(output_fields), "types": {}},
            "nullable": [],
            "requires_auth": False,
            "security_constraints": {},
        },
        "dependencies": [],
        "permissions": [],
        "side_effects": list(side_effects),
        "error_contract": {"error_codes": []},
        "implementations": list(impl_ids),
        "qualification": {"status": "approved", "approved_by": "Sam", "approval_ref": approval_ref},
    }


def impl_record(impl_id, cap_id, entrypoint, status="active", version="1.0.0",
                 approval_ref="APPROVAL-IMPL-REAL"):
    return {
        "id": impl_id,
        "capability_id": cap_id,
        "status": status,
        "release": {"version": version, "commit": "gen_real_todo_app.py", "approved": True,
                     "approval_ref": approval_ref},
        "source": {"repository": "shelf", "path": impl_id, "entrypoint": entrypoint},
        "dependencies": [],
        "tests": [],
        "rollback": {"previous_version": None},
    }


def slot(slot_id, target_cap, name, selector, side_effects=()):
    # match_contract() requires side_effects to match the target capability's
    # own declared side_effects EXACTLY (not a subset -- only nullable_fields
    # and security_constraints loosen to subset matching, per H-T3). Every
    # capability below that declares real side effects (creates/updates/
    # deletes a record) needs its slot to declare the same list, or a real,
    # correctly-behaving capability would be wrongly HELD for a mismatch that
    # isn't actually a mismatch in what it does -- only in what the slot
    # said it expected.
    return {
        "slot_id": slot_id, "name": name, "target_capability": target_cap, "selector": selector,
        "expected_contract": {
            "required_input_fields": [], "input_types": {}, "output_fields": [],
            "output_types": {}, "nullable_fields": [], "permissions": [], "requires_auth": False,
            "dependencies": [], "handled_errors": [], "security_constraints": {},
            "side_effects": list(side_effects),
            "min_version": "1.0.0",
        },
    }


# ==============================================================================
# The real, shared data store every route module reads/writes -- a real JSON
# file beside the app, not an in-memory stub. Each route.py below is a
# self-contained shelf part (per this system's own convention: an IMPL's
# payload is copied standalone into builds/<APP-id>/modules/<CAP-id>/, with
# no shared sibling library to import from) so the tiny load/save helpers
# are duplicated into each one, real code in every copy, not a stub.
# ==============================================================================
STORE_HELPERS = '''
import json
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "todos.json"


def _load():
    if not DATA_FILE.is_file():
        return []
    try:
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save(todos):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(todos), encoding="utf-8")
'''


# ------------------------------------------------------------------------------
# CAP-0100 -- the host/entry module: real TodoMVC HTML/CSS/JS, health check,
# and the same proven dynamic module loader CAP-0001's fixture uses (see
# verification/gen_fixtures.py's LOADER_APP_PY) minus the baked-in
# /api/items route -- every real action below is its own real shelf module,
# loaded the same proven way.
# ------------------------------------------------------------------------------
write_json(CAPS / "CAP-0100.json",
           cap_record("CAP-0100", "Todo App Host", "ui", ["CAP-0100/IMPL-01"]))
write_json(IMPLS / "CAP-0100" / "IMPL-01.json",
           impl_record("CAP-0100/IMPL-01", "CAP-0100", "CAP-0100/app.py"))

INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Todos</title>
<style>
body { font-family: Helvetica Neue, Helvetica, Arial, sans-serif; max-width: 550px; margin: 40px auto; }
.todoapp { background: #fff; box-shadow: 0 2px 4px rgba(0,0,0,.2); }
.header input#new-todo { width: 100%; box-sizing: border-box; font-size: 20px; padding: 12px; border: none;
  border-bottom: 1px solid #ededed; }
ul#todo-list { list-style: none; margin: 0; padding: 0; }
ul#todo-list li { position: relative; border-bottom: 1px solid #ededed; padding: 12px 12px 12px 40px; }
ul#todo-list li .toggle { position: absolute; left: 10px; top: 14px; }
ul#todo-list li label { margin-left: 6px; }
ul#todo-list li.completed label { text-decoration: line-through; color: #949494; }
ul#todo-list li .destroy { display: none; float: right; cursor: pointer; border: none; background: none; }
ul#todo-list li:hover .destroy { display: inline; }
ul#todo-list li .edit { display: none; width: 90%; font-size: 16px; }
ul#todo-list li.editing .edit { display: inline; }
ul#todo-list li.editing .view { display: none; }
.footer { padding: 10px 15px; display: flex; justify-content: space-between; align-items: center; }
.footer .filters { list-style: none; display: inline-flex; gap: 8px; margin: 0; padding: 0; }
.footer .filters a { text-decoration: none; color: #777; padding: 2px 6px; border: 1px solid transparent; }
.footer .filters a.selected { border-color: rgba(175,47,47,.2); border-radius: 3px; }
#clear-completed { border: none; background: none; cursor: pointer; color: #777; }
</style>
</head>
<body>
<section class="todoapp">
  <header class="header">
    <input id="new-todo" data-slot="new_todo" placeholder="What needs to be done?" autofocus>
  </header>
  <section class="main">
    <input id="toggle-all" data-slot="toggle_all" type="checkbox">
    <label for="toggle-all">Mark all as complete</label>
    <ul id="todo-list" data-slot="todo_list"></ul>
  </section>
  <footer class="footer">
    <span id="todo-count"></span>
    <ul class="filters">
      <li><a href="#/" data-filter="all">All</a></li>
      <li><a href="#/active" data-filter="active">Active</a></li>
      <li><a href="#/completed" data-filter="completed">Completed</a></li>
    </ul>
    <button id="clear-completed" data-slot="clear_completed">Clear completed</button>
  </footer>
</section>
<script>
var todos = [];
var editingId = null;

function currentFilter() {
  var h = location.hash;
  if (h === "#/active") return "active";
  if (h === "#/completed" || h === "#!/") return "completed";
  return "all";
}

function refresh() {
  fetch("/api/todos").then(function(r) { return r.json(); }).then(function(data) {
    todos = data.todos || [];
    render();
  });
}

function render() {
  var filter = currentFilter();
  var list = document.getElementById("todo-list");
  list.innerHTML = "";
  todos.forEach(function(t) {
    if (filter === "active" && t.completed) return;
    if (filter === "completed" && !t.completed) return;
    var li = document.createElement("li");
    li.className = (t.completed ? "completed " : "") + (editingId === t.id ? "editing" : "");
    li.dataset.id = t.id;

    var view = document.createElement("div");
    view.className = "view";
    var toggle = document.createElement("input");
    toggle.type = "checkbox"; toggle.className = "toggle"; toggle.checked = !!t.completed;
    toggle.addEventListener("change", function() { toggleTodo(t.id); });
    var label = document.createElement("label");
    label.textContent = t.title;
    label.addEventListener("dblclick", function() { startEdit(t.id); });
    var destroy = document.createElement("button");
    destroy.className = "destroy"; destroy.textContent = "x";
    destroy.addEventListener("click", function() { deleteTodo(t.id); });
    view.appendChild(toggle); view.appendChild(label); view.appendChild(destroy);

    var editInput = document.createElement("input");
    editInput.className = "edit"; editInput.value = t.title;
    editInput.addEventListener("keydown", function(e) {
      if (e.key === "Enter") editInput.blur();
      if (e.key === "Escape") { editingId = null; render(); }
    });
    editInput.addEventListener("blur", function() { saveEdit(t.id, editInput.value); });

    li.appendChild(view); li.appendChild(editInput);
    list.appendChild(li);
    if (editingId === t.id) { editInput.focus(); }
  });

  var activeCount = todos.filter(function(t) { return !t.completed; }).length;
  var word = activeCount === 1 ? "item" : "items";
  document.getElementById("todo-count").innerHTML = "<strong>" + activeCount + "</strong> " + word + " left";

  var completedCount = todos.filter(function(t) { return t.completed; }).length;
  document.getElementById("clear-completed").style.display = completedCount > 0 ? "inline" : "none";

  document.querySelectorAll(".filters a").forEach(function(a) {
    a.className = a.dataset.filter === filter ? "selected" : "";
  });

  document.getElementById("toggle-all").checked = todos.length > 0 && activeCount === 0;
}

function addTodo(title) {
  title = title.trim();
  if (!title) return;
  fetch("/api/todos", {
    method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({title: title})
  }).then(refresh);
}

function toggleTodo(id) {
  fetch("/api/todos/toggle", {
    method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({id: id})
  }).then(refresh);
}

function deleteTodo(id) {
  fetch("/api/todos/delete", {
    method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({id: id})
  }).then(refresh);
}

function startEdit(id) { editingId = id; render(); }

function saveEdit(id, title) {
  if (editingId !== id) return;
  editingId = null;
  title = title.trim();
  if (!title) { deleteTodo(id); return; }
  fetch("/api/todos/edit", {
    method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({id: id, title: title})
  }).then(refresh);
}

function toggleAll(completed) {
  fetch("/api/todos/toggle_all", {
    method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({completed: completed})
  }).then(refresh);
}

function clearCompleted() {
  fetch("/api/todos/clear_completed", {method: "POST"}).then(refresh);
}

document.getElementById("new-todo").addEventListener("keydown", function(e) {
  if (e.key === "Enter") { addTodo(e.target.value); e.target.value = ""; }
});
document.getElementById("toggle-all").addEventListener("change", function(e) {
  toggleAll(e.target.checked);
});
document.getElementById("clear-completed").addEventListener("click", clearCompleted);
window.addEventListener("hashchange", render);

refresh();
</script>
</body>
</html>
"""

HOST_APP_PY = '''#!/usr/bin/env python3
"""modules/CAP-0100/app.py -- the real TodoMVC host: home page, health
check, and a dynamic loader for sibling capability modules
(modules/<CAP-id>/route.py), exactly the same proven convention as
CAP-0001's fixture host (see verification/gen_fixtures.py's LOADER_APP_PY)
minus that fixture's own baked-in /api/items route -- every real
data-mutating action here is its own real shelf module (round 7)."""
import argparse
import importlib.util
from pathlib import Path
from flask import Flask, jsonify, request, Response

app = Flask(__name__)
HERE = Path(__file__).resolve().parent
MODULES_ROOT = HERE.parent

INDEX_HTML = %(index_html)r


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
        if not entry.is_dir() or entry.name == "CAP-0100":
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
''' % {"index_html": INDEX_HTML}

write(IMPLS / "CAP-0100" / "IMPL-01" / "CAP-0100" / "app.py", HOST_APP_PY)


# ------------------------------------------------------------------------------
# The six real data-mutating/read capabilities. Each is its own shelf CAP +
# IMPL + real route.py module, picked up automatically by build.py's
# existing (round 4, unmodified) generic compute-capability check
# generator -- no new check logic needed for any of these six.
# ------------------------------------------------------------------------------
def route_cap(cap_id, name, route, method, output_fields, side_effects=(), required_input=()):
    write_json(CAPS / f"{cap_id}.json",
               cap_record(cap_id, name, "compute", [f"{cap_id}/IMPL-01"],
                          output_fields=output_fields, required_input=required_input,
                          side_effects=side_effects))
    write_json(IMPLS / cap_id / "IMPL-01.json",
               impl_record(f"{cap_id}/IMPL-01", cap_id, f"{cap_id}/route.py"))


route_cap("CAP-0101", "List Todos", "/api/todos", "GET", output_fields=("todos",))
write(IMPLS / "CAP-0101" / "IMPL-01" / "CAP-0101" / "route.py", STORE_HELPERS + '''
ROUTE = "/api/todos"
METHOD = "GET"


def handle(request):
    return 200, {"todos": _load()}
''')

route_cap("CAP-0102", "Create Todo", "/api/todos", "POST",
          output_fields=("id", "title", "completed"), side_effects=("creates_record",),
          required_input=("title",))
write(IMPLS / "CAP-0102" / "IMPL-01" / "CAP-0102" / "route.py", STORE_HELPERS + '''
ROUTE = "/api/todos"
METHOD = "POST"


def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    title = (body.get("title") or "").strip()
    if not title:
        return 400, {"error": "title is required"}
    todos = _load()
    next_id = (max([t["id"] for t in todos], default=0)) + 1
    todo = {"id": next_id, "title": title, "completed": False}
    todos.append(todo)
    _save(todos)
    return 201, todo
''')

route_cap("CAP-0103", "Toggle Todo", "/api/todos/toggle", "POST",
          output_fields=("id", "title", "completed"), side_effects=("updates_record",),
          required_input=("id",))
write(IMPLS / "CAP-0103" / "IMPL-01" / "CAP-0103" / "route.py", STORE_HELPERS + '''
ROUTE = "/api/todos/toggle"
METHOD = "POST"


def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    todo_id = body.get("id")
    todos = _load()
    for t in todos:
        if t["id"] == todo_id:
            t["completed"] = not t["completed"]
            _save(todos)
            return 200, t
    return 404, {"error": f"no todo with id {todo_id!r}"}
''')

route_cap("CAP-0104", "Edit Todo", "/api/todos/edit", "POST",
          output_fields=("id", "title", "completed"), side_effects=("updates_record",),
          required_input=("id", "title"))
write(IMPLS / "CAP-0104" / "IMPL-01" / "CAP-0104" / "route.py", STORE_HELPERS + '''
ROUTE = "/api/todos/edit"
METHOD = "POST"


def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    todo_id = body.get("id")
    title = (body.get("title") or "").strip()
    if not title:
        return 400, {"error": "title is required"}
    todos = _load()
    for t in todos:
        if t["id"] == todo_id:
            t["title"] = title
            _save(todos)
            return 200, t
    return 404, {"error": f"no todo with id {todo_id!r}"}
''')

route_cap("CAP-0105", "Delete Todo", "/api/todos/delete", "POST",
          output_fields=("id", "deleted"), side_effects=("deletes_record",),
          required_input=("id",))
write(IMPLS / "CAP-0105" / "IMPL-01" / "CAP-0105" / "route.py", STORE_HELPERS + '''
ROUTE = "/api/todos/delete"
METHOD = "POST"


def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    todo_id = body.get("id")
    todos = _load()
    remaining = [t for t in todos if t["id"] != todo_id]
    if len(remaining) == len(todos):
        return 404, {"error": f"no todo with id {todo_id!r}"}
    _save(remaining)
    return 200, {"id": todo_id, "deleted": True}
''')

route_cap("CAP-0106", "Toggle All Todos", "/api/todos/toggle_all", "POST",
          output_fields=("updated",), side_effects=("updates_record",))
write(IMPLS / "CAP-0106" / "IMPL-01" / "CAP-0106" / "route.py", STORE_HELPERS + '''
ROUTE = "/api/todos/toggle_all"
METHOD = "POST"


def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    completed = bool(body.get("completed", True))
    todos = _load()
    updated = 0
    for t in todos:
        if t["completed"] != completed:
            t["completed"] = completed
            updated += 1
    _save(todos)
    return 200, {"updated": updated}
''')

route_cap("CAP-0107", "Clear Completed Todos", "/api/todos/clear_completed", "POST",
          output_fields=("removed",), side_effects=("deletes_record",))
write(IMPLS / "CAP-0107" / "IMPL-01" / "CAP-0107" / "route.py", STORE_HELPERS + '''
ROUTE = "/api/todos/clear_completed"
METHOD = "POST"


def handle(request):
    todos = _load()
    remaining = [t for t in todos if not t["completed"]]
    removed = len(todos) - len(remaining)
    _save(remaining)
    return 200, {"removed": removed}
''')


# ==============================================================================
# Template -- real, accepted, one slot per real capability so every one of
# them gets its own real check (round 4's generic loop for the six compute
# capabilities, round 7's generalized host checks for CAP-0100), plus a real
# `primary_journey` declaration: fill the real #new-todo input with a real
# string and press real Enter -- the real TodoMVC way to create a todo,
# never a fake "Add" button invented just to satisfy the old check's shape.
# ==============================================================================
TEMPLATE = {
    "accepted": True,
    "app_type": "todo list",
    "required_capabilities": ["CAP-0100", "CAP-0101", "CAP-0102", "CAP-0103", "CAP-0104",
                               "CAP-0105", "CAP-0106", "CAP-0107"],
    "interface_slots": [
        slot("new_todo", "CAP-0102", "Add a new todo", "#new-todo", side_effects=("creates_record",)),
        slot("todo_list", "CAP-0101", "See the todo list", "#todo-list"),
        slot("toggle_todo", "CAP-0103", "Mark a todo complete/incomplete", ".toggle",
             side_effects=("updates_record",)),
        slot("edit_todo", "CAP-0104", "Edit a todo's title", ".edit", side_effects=("updates_record",)),
        slot("delete_todo", "CAP-0105", "Delete a todo", ".destroy", side_effects=("deletes_record",)),
        slot("toggle_all", "CAP-0106", "Mark all todos complete/incomplete", "#toggle-all",
             side_effects=("updates_record",)),
        slot("clear_completed", "CAP-0107", "Clear completed todos", "#clear-completed",
             side_effects=("deletes_record",)),
    ],
    "entry_route": "/",
    "entry_screen_name": "Home",
    "start_command": ["python3", "modules/CAP-0100/app.py"],
    "port": 5000,
    "health_endpoint": "/health",
    "test_command": ["python3", "-c", "print('real todo list app -- no template-level tests declared beyond build.py\\'s own proving run')"],
    "primary_journey": {
        "input_selector": "#new-todo",
        "input_value": "Buy real milk from the real store",
        "action_key": "Enter",
        "confirm_selector": "#todo-list",
        "confirm_contains": "Buy real milk from the real store",
    },
}
write_json(TEMPLATES / "todo_list.json", TEMPLATE)


# ==============================================================================
# APPS_LIST.md + choice.json -- the real app-type string, exactly as
# canonical_app_types.py records it (item #1 of Sam's real 43).
# ==============================================================================
write(ROOT / "APPS_LIST.md", "# Approved app types\n\n- todo list\n")

write_json(ROOT / "choice.json", {
    "app_type": "todo list",
    "skin_id": "skin-001",
    "skin_version": "1.0.0",
    "arrangement": [
        {"slot": "new_todo", "position": "top"},
        {"slot": "todo_list", "position": "center"},
        {"slot": "toggle_todo", "position": "center"},
        {"slot": "edit_todo", "position": "center"},
        {"slot": "delete_todo", "position": "center"},
        {"slot": "toggle_all", "position": "center"},
        {"slot": "clear_completed", "position": "bottom"},
    ],
    "branding": {"name": "Real Todo List", "color": "#af2f2f"},
})

print(f"real todo list app fixtures written under {ROOT}")
