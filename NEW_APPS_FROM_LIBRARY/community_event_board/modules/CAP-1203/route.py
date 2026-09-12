
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

ROUTE = '/api/messages/delete'
METHOD = 'POST'


def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    mid = body.get('id')
    messages = _load()
    remaining = [m for m in messages if m['id'] != mid]
    if len(remaining) == len(messages):
        return 404, {'error': f'no message with id {mid!r}'}
    _save(remaining)
    return 200, {'id': mid, 'deleted': True}
