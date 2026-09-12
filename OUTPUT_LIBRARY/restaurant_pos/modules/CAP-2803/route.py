
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

ROUTE = '/api/orders/close'
METHOD = 'POST'


def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    oid = body.get('id')
    orders = _load()
    for o in orders:
        if o['id'] == oid:
            o['status'] = 'closed'
            _save(orders)
            return 200, o
    return 404, {'error': f'no order with id {oid!r}'}
