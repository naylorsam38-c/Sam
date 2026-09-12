
import json
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "project_management.json"


def _load():
    if not DATA_FILE.is_file():
        return []
    try:
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save(rows):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(rows), encoding="utf-8")

ROUTE = '/api/tasks/status'
METHOD = 'POST'


def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    tid = body.get('id')
    status = body.get('status') or 'todo'
    tasks = _load()
    for t in tasks:
        if t['id'] == tid:
            t['status'] = status
            _save(tasks)
            return 200, t
    return 404, {'error': f'no task with id {tid!r}'}
