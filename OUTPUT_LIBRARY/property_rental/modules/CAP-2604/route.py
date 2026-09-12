
import json
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "bookings.json"


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

ROUTE = '/api/bookings'
METHOD = 'POST'


def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    listing_id = body.get('listing_id')
    guest = (body.get('guest') or '').strip()
    if listing_id is None or not guest:
        return 400, {'error': 'listing_id and guest are required'}
    bookings = _load()
    next_id = (max([b['id'] for b in bookings], default=0)) + 1
    booking = {'id': next_id, 'listing_id': listing_id, 'guest': guest}
    bookings.append(booking)
    _save(bookings)
    return 201, booking
