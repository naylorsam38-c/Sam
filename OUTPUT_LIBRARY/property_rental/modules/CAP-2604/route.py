
import importlib.util as _importlib_util
from pathlib import Path as _Path

_shared_lib_path = _Path(__file__).resolve().parents[1] / "CAP-0000" / "shared_lib.py"
_spec = _importlib_util.spec_from_file_location("cap0000_shared_lib", _shared_lib_path)
_shared = _importlib_util.module_from_spec(_spec)
_spec.loader.exec_module(_shared)

DATA_FILE_NAME = "bookings.json"


def _load():
    return _shared.load(DATA_FILE_NAME)


def _save(rows):
    _shared.save(DATA_FILE_NAME, rows)

ROUTE = '/api/property_rental/bookings'
METHOD = 'POST'


def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    listing_id = body.get('listing_id')
    guest = (body.get('guest') or '').strip()
    if listing_id is None or not guest:
        return 400, {'error': 'listing_id and guest are required'}
    bookings = _load()
    next_id = (max([b['id'] for b in bookings], default=0)) + 1
    booking = {'id': next_id, 'listing_id': listing_id, 'guest': guest}
    bookings.append(booking)
    _save(bookings)
    return 201, booking
