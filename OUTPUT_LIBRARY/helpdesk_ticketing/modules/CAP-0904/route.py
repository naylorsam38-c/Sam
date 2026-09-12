
import json
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "helpdesk_ticketing.json"


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

ROUTE = '/api/tickets/delete'
METHOD = 'POST'


def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    tid = body.get('id')
    tickets = _load()
    remaining = [t for t in tickets if t['id'] != tid]
    if len(remaining) == len(tickets):
        return 404, {'error': f'no ticket with id {tid!r}'}
    _save(remaining)
    return 200, {'id': tid, 'deleted': True}
