
import json
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "restaurant_pos.json"


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

ROUTE = '/api/orders'
METHOD = 'POST'


def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    item = (body.get('item') or '').strip()
    if not item:
        return 400, {'error': 'item is required'}
    try:
        total = float(body.get('total', 0) or 0)
    except (TypeError, ValueError):
        total = 0.0
    orders = _load()
    next_id = (max([o['id'] for o in orders], default=0)) + 1
    order = {'id': next_id, 'item': item, 'total': total, 'status': 'open'}
    orders.append(order)
    _save(orders)
    return 201, order
