
import importlib.util as _importlib_util
from pathlib import Path as _Path

_shared_lib_path = _Path(__file__).resolve().parents[1] / "CAP-0000" / "shared_lib.py"
_spec = _importlib_util.spec_from_file_location("cap0000_shared_lib", _shared_lib_path)
_shared = _importlib_util.module_from_spec(_spec)
_spec.loader.exec_module(_shared)

DATA_FILE_NAME = "vendor_products.json"


def _load():
    return _shared.load(DATA_FILE_NAME)


def _save(rows):
    _shared.save(DATA_FILE_NAME, rows)

ROUTE = '/api/multi_vendor_marketplace/vendor_products'
METHOD = 'POST'


def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    vendor_id = body.get('vendor_id')
    name = (body.get('name') or '').strip()
    if vendor_id is None or not name:
        return 400, {'error': 'vendor_id and name are required'}
    products = _load()
    next_id = (max([p['id'] for p in products], default=0)) + 1
    product = {'id': next_id, 'vendor_id': vendor_id, 'name': name}
    products.append(product)
    _save(products)
    return 201, product
