
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

ROUTE = '/api/events'
METHOD = 'POST'


def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    title = (body.get('title') or '').strip()
    if not title:
        return 400, {'error': 'title is required'}
    try:
        capacity = int(body.get('capacity', 100) or 100)
    except (TypeError, ValueError):
        capacity = 100
    events = _load()
    next_id = (max([e['id'] for e in events], default=0)) + 1
    ev = {'id': next_id, 'title': title, 'capacity': capacity, 'sold': 0}
    events.append(ev)
    _save(events)
    return 201, ev
