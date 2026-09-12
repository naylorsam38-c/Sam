
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

ROUTE = '/api/events/delete'
METHOD = 'POST'


def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    eid = body.get('id')
    events = _load()
    remaining = [e for e in events if e['id'] != eid]
    if len(remaining) == len(events):
        return 404, {'error': f'no event with id ' + repr(eid)}
    _save(remaining)
    return 200, {'id': eid, 'deleted': True}
