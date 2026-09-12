
import json
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "orders.json"


def _load():
    if not DATA_FILE.is_file():
        return []
    try:
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save(rows):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(rows), encoding="utf-8")

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
