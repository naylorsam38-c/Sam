
import json
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "notifications.json"


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

ROUTE = '/api/notifications'
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
