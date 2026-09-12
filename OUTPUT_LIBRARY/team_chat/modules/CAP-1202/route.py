
import json
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "team_chat.json"


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

ROUTE = '/api/messages'
METHOD = 'POST'


def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    text = (body.get('text') or '').strip()
    if not text:
        return 400, {'error': 'text is required'}
    author = body.get('author') or 'You'
    messages = _load()
    next_id = (max([m['id'] for m in messages], default=0)) + 1
    msg = {'id': next_id, 'author': author, 'text': text}
    messages.append(msg)
    _save(messages)
    return 201, msg
