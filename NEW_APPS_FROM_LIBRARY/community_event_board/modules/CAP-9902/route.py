
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

ROUTE = '/api/events'
METHOD = 'POST'


import datetime
def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    title = (body.get('title') or '').strip()
    if not title:
        return 400, {'error': 'title is required'}
    start_raw = body.get('start') or ''
    try:
        start_dt = datetime.datetime.fromisoformat(start_raw)
    except (TypeError, ValueError):
        return 400, {'error': f'start is not a valid ISO-8601 timestamp: {start_raw!r}'}
    end_raw = body.get('end') or ''
    end_dt = None
    if end_raw:
        try:
            end_dt = datetime.datetime.fromisoformat(end_raw)
        except (TypeError, ValueError):
            return 400, {'error': f'end is not a valid ISO-8601 timestamp: {end_raw!r}'}
        if end_dt < start_dt:
            return 400, {'error': 'end must not be before start'}
    try:
        capacity_val = int(body.get('capacity', 10) or 10)
    except (TypeError, ValueError):
        capacity_val = 10
    attendees_val = 0
    events = _load()
    next_id = (max([e['id'] for e in events], default=0)) + 1
    ev = {'id': next_id, 'title': title, 'start': start_dt.isoformat(),
          'end': end_dt.isoformat() if end_dt else None}
    ev['capacity'] = capacity_val
    ev['attendees'] = attendees_val
    events.append(ev)
    _save(events)
    return 201, ev
