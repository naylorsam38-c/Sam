
import json
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "event_ticketing.json"


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

ROUTE = '/api/events/buy'
METHOD = 'POST'


def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    eid = body.get('id')
    events = _load()
    for e in events:
        if e['id'] == eid:
            if e['sold'] >= e['capacity']:
                return 400, {'error': 'sold out'}
            e['sold'] += 1
            _save(events)
            return 200, e
    return 404, {'error': f'no event with id {eid!r}'}
