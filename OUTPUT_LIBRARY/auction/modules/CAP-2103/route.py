
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

ROUTE = '/api/items/bid'
METHOD = 'POST'


def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    iid = body.get('id')
    bidder = body.get('bidder') or 'anonymous'
    try:
        amount = float(body.get('amount', 0) or 0)
    except (TypeError, ValueError):
        amount = 0.0
    items = _load()
    for i in items:
        if i['id'] == iid:
            if amount <= i.get('current_bid', 0):
                return 400, {'error': 'bid too low'}
            i['current_bid'] = amount
            i['highest_bidder'] = bidder
            _save(items)
            return 200, i
    return 404, {'error': f'no item with id {iid!r}'}
