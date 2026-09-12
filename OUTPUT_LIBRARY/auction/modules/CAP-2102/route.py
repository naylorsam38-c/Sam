
import json
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "auction.json"


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
    title = (body.get('title') or '').strip()
    if not title:
        return 400, {'error': 'title is required'}
    try:
        starting_bid = float(body.get('starting_bid', 0) or 0)
    except (TypeError, ValueError):
        starting_bid = 0.0
    items = _load()
    next_id = (max([i['id'] for i in items], default=0)) + 1
    item = {'id': next_id, 'title': title, 'current_bid': starting_bid, 'highest_bidder': None}
    items.append(item)
    _save(items)
    return 201, item
