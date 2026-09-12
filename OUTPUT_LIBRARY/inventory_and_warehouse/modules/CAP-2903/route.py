
import importlib.util as _importlib_util
from pathlib import Path as _Path

_shared_lib_path = _Path(__file__).resolve().parents[1] / "CAP-0000" / "shared_lib.py"
_spec = _importlib_util.spec_from_file_location("cap0000_shared_lib", _shared_lib_path)
_shared = _importlib_util.module_from_spec(_spec)
_spec.loader.exec_module(_shared)

DATA_FILE_NAME = "inventory_and_warehouse.json"


def _load():
    return _shared.load(DATA_FILE_NAME)


def _save(rows):
    _shared.save(DATA_FILE_NAME, rows)

ROUTE = '/api/inventory_and_warehouse/items/adjust'
METHOD = 'POST'


def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    iid = body.get('id')
    try:
        delta = int(body.get('delta', 0) or 0)
    except (TypeError, ValueError):
        delta = 0
    items = _load()
    for i in items:
        if i['id'] == iid:
            i['qty'] = i.get('qty', 0) + delta
            _save(items)
            return 200, i
    return 404, {'error': f'no item with id {iid!r}'}
