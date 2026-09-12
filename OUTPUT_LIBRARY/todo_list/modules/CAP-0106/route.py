
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
