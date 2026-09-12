
import importlib.util as _importlib_util
from pathlib import Path as _Path

_shared_lib_path = _Path(__file__).resolve().parents[1] / "CAP-0000" / "shared_lib.py"
_spec = _importlib_util.spec_from_file_location("cap0000_shared_lib", _shared_lib_path)
_shared = _importlib_util.module_from_spec(_spec)
_spec.loader.exec_module(_shared)

DATA_FILE_NAME = "orders.json"


def _load():
    return _shared.load(DATA_FILE_NAME)


def _save(rows):
    _shared.save(DATA_FILE_NAME, rows)

ROUTE = '/api/checkout'
METHOD = 'POST'


def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    product_id = body.get('product_id')
    if product_id is None:
        return 400, {'error': 'product_id is required'}
    orders = _load()
    next_id = (max([o['id'] for o in orders], default=0)) + 1
    # Real order record; NOT a real payment settlement -- no payment
    # processor is wired in this sandbox, named plainly here.
    order = {'id': next_id, 'product_id': product_id, 'status': 'placed', 'payment': 'not_processed'}
    orders.append(order)
    _save(orders)
    return 201, order
