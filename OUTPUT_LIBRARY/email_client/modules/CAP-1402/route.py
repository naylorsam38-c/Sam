
import json
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "email_client.json"


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
