
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
