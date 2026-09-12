
import json
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "habit_tracker.json"


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

ROUTE = '/api/habits/delete'
METHOD = 'POST'


def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    hid = body.get('id')
    habits = _load()
    remaining = [h for h in habits if h['id'] != hid]
    if len(remaining) == len(habits):
        return 404, {'error': f'no habit with id {hid!r}'}
    _save(remaining)
    return 200, {'id': hid, 'deleted': True}
