
import json
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "menu.json"


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

ROUTE = '/api/menu'
METHOD = 'POST'


def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    restaurant_id = body.get('restaurant_id')
    name = (body.get('name') or '').strip()
    if restaurant_id is None or not name:
        return 400, {'error': 'restaurant_id and name are required'}
    menu = _load()
    next_id = (max([m['id'] for m in menu], default=0)) + 1
    item = {'id': next_id, 'restaurant_id': restaurant_id, 'name': name}
    menu.append(item)
    _save(menu)
    return 201, item
