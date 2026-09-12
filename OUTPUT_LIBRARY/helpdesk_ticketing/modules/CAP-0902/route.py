
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

ROUTE = '/api/tickets'
METHOD = 'POST'


def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    subject = (body.get('subject') or '').strip()
    if not subject:
        return 400, {'error': 'subject is required'}
    tickets = _load()
    next_id = (max([t['id'] for t in tickets], default=0)) + 1
    ticket = {'id': next_id, 'subject': subject, 'status': 'open'}
    tickets.append(ticket)
    _save(tickets)
    return 201, ticket
