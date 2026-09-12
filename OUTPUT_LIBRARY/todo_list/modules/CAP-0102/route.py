
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
