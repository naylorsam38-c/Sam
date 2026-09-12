
import json
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "events.json"


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

ROUTE = '/api/events/rsvp'
METHOD = 'POST'


def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    rid = body.get('id')
    rows = _load()
    for rec in rows:
        if rec['id'] == rid:
            if rec['attendees'] >= rec['capacity']:
                return 400, {'error': 'event is full'}
            rec['attendees'] += 1
            _save(rows)
            return 200, rec
    return 404, {'error': f'no event with id ' + repr(rid)}
