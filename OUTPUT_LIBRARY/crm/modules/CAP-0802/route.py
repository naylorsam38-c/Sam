
import importlib.util as _importlib_util
from pathlib import Path as _Path

_shared_lib_path = _Path(__file__).resolve().parents[1] / "CAP-0000" / "shared_lib.py"
_spec = _importlib_util.spec_from_file_location("cap0000_shared_lib", _shared_lib_path)
_shared = _importlib_util.module_from_spec(_spec)
_spec.loader.exec_module(_shared)

DATA_FILE_NAME = "crm.json"


def _load():
    return _shared.load(DATA_FILE_NAME)


def _save(rows):
    _shared.save(DATA_FILE_NAME, rows)

ROUTE = '/api/crm/contacts'
METHOD = 'POST'


def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    name = (body.get('name') or '').strip()
    if not name:
        return 400, {'error': 'name is required'}
    email = body.get('email') or ''
    contacts = _load()
    next_id = (max([c['id'] for c in contacts], default=0)) + 1
    contact = {'id': next_id, 'name': name, 'email': email, 'stage': 'lead'}
    contacts.append(contact)
    _save(contacts)
    return 201, contact
