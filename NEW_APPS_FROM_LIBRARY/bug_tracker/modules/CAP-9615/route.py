
import importlib.util as _importlib_util
from pathlib import Path as _Path

_shared_lib_path = _Path(__file__).resolve().parents[1] / "CAP-0000" / "shared_lib.py"
_spec = _importlib_util.spec_from_file_location("cap0000_shared_lib", _shared_lib_path)
_shared = _importlib_util.module_from_spec(_spec)
_spec.loader.exec_module(_shared)

DATA_FILE_NAME = "notifications.json"


def _load():
    return _shared.load(DATA_FILE_NAME)


def _save(rows):
    _shared.save(DATA_FILE_NAME, rows)

ROUTE = '/api/bug_tracker/notifications'
METHOD = 'POST'


def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    recipient = (body.get('recipient') or '').strip()
    message = (body.get('message') or '').strip()
    if not recipient or not message:
        return 400, {'error': 'recipient and message are required'}
    rows = _load()
    next_id = (max([r['id'] for r in rows], default=0)) + 1
    note = {'id': next_id, 'recipient': recipient, 'message': message, 'read': False}
    rows.append(note)
    _save(rows)
    return 201, note
