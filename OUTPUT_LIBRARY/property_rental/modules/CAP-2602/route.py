
import json
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "listings.json"


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

ROUTE = '/api/listings'
METHOD = 'POST'


def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    title = (body.get('title') or '').strip()
    if not title:
        return 400, {'error': 'title is required'}
    try:
        price = float(body.get('price', 0) or 0)
    except (TypeError, ValueError):
        price = 0.0
    listings = _load()
    next_id = (max([l['id'] for l in listings], default=0)) + 1
    listing = {'id': next_id, 'title': title, 'price': price}
    listings.append(listing)
    _save(listings)
    return 201, listing
