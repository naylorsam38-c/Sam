
import importlib.util as _importlib_util
from pathlib import Path as _Path

_shared_lib_path = _Path(__file__).resolve().parents[1] / "CAP-0000" / "shared_lib.py"
_spec = _importlib_util.spec_from_file_location("cap0000_shared_lib", _shared_lib_path)
_shared = _importlib_util.module_from_spec(_spec)
_spec.loader.exec_module(_shared)

DATA_FILE_NAME = "sessions.json"


def _load():
    return _shared.load(DATA_FILE_NAME)


def _save(rows):
    _shared.save(DATA_FILE_NAME, rows)

ROUTE = '/api/course_enrollment_hub/events'
METHOD = 'POST'


import datetime
def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    title = (body.get('title') or '').strip()
    if not title:
        return 400, {'error': 'title is required'}
    start_raw = body.get('start') or ''
    try:
        start_dt = datetime.datetime.fromisoformat(start_raw)
    except (TypeError, ValueError):
        return 400, {'error': f'start is not a valid ISO-8601 timestamp: {start_raw!r}'}
    end_raw = body.get('end') or ''
    end_dt = None
    if end_raw:
        try:
            end_dt = datetime.datetime.fromisoformat(end_raw)
        except (TypeError, ValueError):
            return 400, {'error': f'end is not a valid ISO-8601 timestamp: {end_raw!r}'}
        if end_dt < start_dt:
            return 400, {'error': 'end must not be before start'}
    try:
        seats_val = int(body.get('seats', 20) or 20)
    except (TypeError, ValueError):
        seats_val = 20
    enrolled_val = 0
    events = _load()
    next_id = (max([e['id'] for e in events], default=0)) + 1
    ev = {'id': next_id, 'title': title, 'start': start_dt.isoformat(),
          'end': end_dt.isoformat() if end_dt else None}
    ev['seats'] = seats_val
    ev['enrolled'] = enrolled_val
    events.append(ev)
    _save(events)
    return 201, ev
