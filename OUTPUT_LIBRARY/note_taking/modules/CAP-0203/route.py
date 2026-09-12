
import json
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "note_taking.json"


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

ROUTE = '/api/notes/update'
METHOD = 'POST'


def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    nid = body.get('id')
    notes = _load()
    for n in notes:
        if n['id'] == nid:
            n['title'] = (body.get('title') or n['title']).strip()
            n['body'] = body.get('body', n['body'])
            _save(notes)
            return 200, n
    return 404, {'error': f'no note with id {nid!r}'}
