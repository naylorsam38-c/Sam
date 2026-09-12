
import importlib.util as _importlib_util
from pathlib import Path as _Path

_shared_lib_path = _Path(__file__).resolve().parents[1] / "CAP-0000" / "shared_lib.py"
_spec = _importlib_util.spec_from_file_location("cap0000_shared_lib", _shared_lib_path)
_shared = _importlib_util.module_from_spec(_spec)
_spec.loader.exec_module(_shared)

DATA_FILE_NAME = "helpdesk_ticketing.json"


def _load():
    return _shared.load(DATA_FILE_NAME)


def _save(rows):
    _shared.save(DATA_FILE_NAME, rows)

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
