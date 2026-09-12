
import json
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "inventory_and_warehouse.json"


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

ROUTE = '/api/items'
METHOD = 'POST'


def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    name = (body.get('name') or '').strip()
    if not name:
        return 400, {'error': 'name is required'}
    sku = body.get('sku') or ''
    try:
        qty = int(body.get('qty', 0) or 0)
    except (TypeError, ValueError):
        qty = 0
    items = _load()
    next_id = (max([i['id'] for i in items], default=0)) + 1
    item = {'id': next_id, 'name': name, 'sku': sku, 'qty': qty}
    items.append(item)
    _save(items)
    return 201, item
