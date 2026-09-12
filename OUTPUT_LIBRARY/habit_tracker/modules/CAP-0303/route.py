
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

ROUTE = '/api/habits/checkin'
METHOD = 'POST'


import datetime
def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    hid = body.get('id')
    today = datetime.date.today().isoformat()
    habits = _load()
    for h in habits:
        if h['id'] == hid:
            if today not in h['log']:
                h['log'].append(today)
                h['streak'] += 1
            _save(habits)
            return 200, h
    return 404, {'error': f'no habit with id {hid!r}'}
