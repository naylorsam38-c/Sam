
import importlib.util as _importlib_util
from pathlib import Path as _Path

_shared_lib_path = _Path(__file__).resolve().parents[1] / "CAP-0000" / "shared_lib.py"
_spec = _importlib_util.spec_from_file_location("cap0000_shared_lib", _shared_lib_path)
_shared = _importlib_util.module_from_spec(_spec)
_spec.loader.exec_module(_shared)

DATA_FILE_NAME = "parcel_tracking.json"


def _load():
    return _shared.load(DATA_FILE_NAME)


def _save(rows):
    _shared.save(DATA_FILE_NAME, rows)

ROUTE = '/api/parcels'
METHOD = 'POST'


def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    tracking_no = (body.get('tracking_no') or '').strip()
    if not tracking_no:
        return 400, {'error': 'tracking_no is required'}
    parcels = _load()
    next_id = (max([p['id'] for p in parcels], default=0)) + 1
    parcel = {'id': next_id, 'tracking_no': tracking_no, 'status': 'created', 'history': ['created']}
    parcels.append(parcel)
    _save(parcels)
    return 201, parcel
