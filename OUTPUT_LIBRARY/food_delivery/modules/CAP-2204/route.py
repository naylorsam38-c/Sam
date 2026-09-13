
import importlib.util as _importlib_util
from pathlib import Path as _Path

_shared_lib_path = _Path(__file__).resolve().parents[1] / "CAP-0000" / "shared_lib.py"
_spec = _importlib_util.spec_from_file_location("cap0000_shared_lib", _shared_lib_path)
_shared = _importlib_util.module_from_spec(_spec)
_spec.loader.exec_module(_shared)

DATA_FILE_NAME = "menu.json"


def _load():
    return _shared.load(DATA_FILE_NAME)


def _save(rows):
    _shared.save(DATA_FILE_NAME, rows)

ROUTE = '/api/food_delivery/menu'
METHOD = 'POST'


def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    restaurant_id = body.get('restaurant_id')
    name = (body.get('name') or '').strip()
    if restaurant_id is None or not name:
        return 400, {'error': 'restaurant_id and name are required'}
    menu = _load()
    next_id = (max([m['id'] for m in menu], default=0)) + 1
    item = {'id': next_id, 'restaurant_id': restaurant_id, 'name': name}
    menu.append(item)
    _save(menu)
    return 201, item
