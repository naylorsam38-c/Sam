
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

ROUTE = "/api/todos/clear_completed"
METHOD = "POST"


def handle(request):
    todos = _load()
    remaining = [t for t in todos if not t["completed"]]
    removed = len(todos) - len(remaining)
    _save(remaining)
    return 200, {"removed": removed}
