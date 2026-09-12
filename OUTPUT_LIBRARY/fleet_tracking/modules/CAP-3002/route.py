
import importlib.util as _importlib_util
from pathlib import Path as _Path

_shared_lib_path = _Path(__file__).resolve().parents[1] / "CAP-0000" / "shared_lib.py"
_spec = _importlib_util.spec_from_file_location("cap0000_shared_lib", _shared_lib_path)
_shared = _importlib_util.module_from_spec(_spec)
_spec.loader.exec_module(_shared)

DATA_FILE_NAME = "fleet_tracking.json"


def _load():
    return _shared.load(DATA_FILE_NAME)


def _save(rows):
    _shared.save(DATA_FILE_NAME, rows)

ROUTE = '/api/fleet_tracking/vehicles'
METHOD = 'POST'


def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    name = (body.get('name') or '').strip()
    if not name:
        return 400, {'error': 'name is required'}
    vehicles = _load()
    next_id = (max([v['id'] for v in vehicles], default=0)) + 1
    vehicle = {'id': next_id, 'name': name, 'status': 'idle', 'location': ''}
    vehicles.append(vehicle)
    _save(vehicles)
    return 201, vehicle
