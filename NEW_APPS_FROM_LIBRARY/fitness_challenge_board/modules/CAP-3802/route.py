
import importlib.util as _importlib_util
from pathlib import Path as _Path

_shared_lib_path = _Path(__file__).resolve().parents[1] / "CAP-0000" / "shared_lib.py"
_spec = _importlib_util.spec_from_file_location("cap0000_shared_lib", _shared_lib_path)
_shared = _importlib_util.module_from_spec(_spec)
_spec.loader.exec_module(_shared)

DATA_FILE_NAME = "fitness_tracking.json"


def _load():
    return _shared.load(DATA_FILE_NAME)


def _save(rows):
    _shared.save(DATA_FILE_NAME, rows)

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
