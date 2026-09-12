
import json
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "fitness_tracking.json"


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

ROUTE = '/api/workouts'
METHOD = 'POST'


def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    wtype = (body.get('type') or '').strip()
    if not wtype:
        return 400, {'error': 'type is required'}
    try:
        duration = float(body.get('duration', 0) or 0)
    except (TypeError, ValueError):
        duration = 0.0
    workouts = _load()
    next_id = (max([w['id'] for w in workouts], default=0)) + 1
    workout = {'id': next_id, 'type': wtype, 'duration': duration}
    workouts.append(workout)
    _save(workouts)
    return 201, workout
