
import json
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "products.json"


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

ROUTE = '/api/products'
METHOD = 'POST'


def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    name = (body.get('name') or '').strip()
    if not name:
        return 400, {'error': 'name is required'}
    try:
        price = float(body.get('price', 0) or 0)
    except (TypeError, ValueError):
        price = 0.0
    products = _load()
    next_id = (max([p['id'] for p in products], default=0)) + 1
    product = {'id': next_id, 'name': name, 'price': price}
    products.append(product)
    _save(products)
    return 201, product
