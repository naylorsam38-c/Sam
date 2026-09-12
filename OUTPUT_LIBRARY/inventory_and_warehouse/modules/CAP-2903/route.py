
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

ROUTE = '/api/items/adjust'
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
