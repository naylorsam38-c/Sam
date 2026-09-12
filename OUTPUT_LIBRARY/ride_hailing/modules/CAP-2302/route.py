
import importlib.util as _importlib_util
from pathlib import Path as _Path

_shared_lib_path = _Path(__file__).resolve().parents[1] / "CAP-0000" / "shared_lib.py"
_spec = _importlib_util.spec_from_file_location("cap0000_shared_lib", _shared_lib_path)
_shared = _importlib_util.module_from_spec(_spec)
_spec.loader.exec_module(_shared)

DATA_FILE_NAME = "ride_hailing.json"


def _load():
    return _shared.load(DATA_FILE_NAME)


def _save(rows):
    _shared.save(DATA_FILE_NAME, rows)

ROUTE = '/api/rides'
METHOD = 'POST'


def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    pickup = (body.get('pickup') or '').strip()
    if not pickup:
        return 400, {'error': 'pickup is required'}
    dropoff = body.get('dropoff') or ''
    rides = _load()
    next_id = (max([r['id'] for r in rides], default=0)) + 1
    ride = {'id': next_id, 'pickup': pickup, 'dropoff': dropoff, 'status': 'requested'}
    rides.append(ride)
    _save(rides)
    return 201, ride
