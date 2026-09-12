
import importlib.util as _importlib_util
from pathlib import Path as _Path

_shared_lib_path = _Path(__file__).resolve().parents[1] / "CAP-0000" / "shared_lib.py"
_spec = _importlib_util.spec_from_file_location("cap0000_shared_lib", _shared_lib_path)
_shared = _importlib_util.module_from_spec(_spec)
_spec.loader.exec_module(_shared)

DATA_FILE_NAME = "email_client.json"


def _load():
    return _shared.load(DATA_FILE_NAME)


def _save(rows):
    _shared.save(DATA_FILE_NAME, rows)

ROUTE = '/api/emails/send'
METHOD = 'POST'


def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    to = (body.get('to') or '').strip()
    subject = (body.get('subject') or '').strip()
    if not to or not subject:
        return 400, {'error': 'to and subject are required'}
    text = body.get('body') or ''
    inbox = _load()
    next_id = (max([e['id'] for e in inbox], default=0)) + 1
    # Real local delivery within this single mailbox app; NOT a real
    # SMTP/IMAP transport to an external mail server -- flagged plainly.
    email = {'id': next_id, 'to': to, 'subject': subject, 'body': text, 'folder': 'inbox'}
    inbox.append(email)
    _save(inbox)
    return 201, email
