
import json
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "vendor_products.json"


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

ROUTE = '/api/vendor_products'
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
