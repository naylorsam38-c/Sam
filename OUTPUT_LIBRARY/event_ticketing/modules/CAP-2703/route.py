
import importlib.util as _importlib_util
from pathlib import Path as _Path

_shared_lib_path = _Path(__file__).resolve().parents[1] / "CAP-0000" / "shared_lib.py"
_spec = _importlib_util.spec_from_file_location("cap0000_shared_lib", _shared_lib_path)
_shared = _importlib_util.module_from_spec(_spec)
_spec.loader.exec_module(_shared)

DATA_FILE_NAME = "event_ticketing.json"


def _load():
    return _shared.load(DATA_FILE_NAME)


def _save(rows):
    _shared.save(DATA_FILE_NAME, rows)

ROUTE = '/api/events/buy'
METHOD = 'POST'


def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    eid = body.get('id')
    events = _load()
    for e in events:
        if e['id'] == eid:
            if e['sold'] >= e['capacity']:
                return 400, {'error': 'sold out'}
            e['sold'] += 1
            _save(events)
            return 200, e
    return 404, {'error': f'no event with id {eid!r}'}
