
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

ROUTE = '/api/tasks'
METHOD = 'POST'


def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    title = (body.get('title') or '').strip()
    if not title:
        return 400, {'error': 'title is required'}
    tasks = _load()
    next_id = (max([t['id'] for t in tasks], default=0)) + 1
    task = {'id': next_id, 'title': title, 'status': 'todo'}
    tasks.append(task)
    _save(tasks)
    return 201, task
