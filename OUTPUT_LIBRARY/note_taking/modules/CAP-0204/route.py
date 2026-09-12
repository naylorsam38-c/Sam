
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

ROUTE = '/api/notes/delete'
METHOD = 'POST'


def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    nid = body.get('id')
    notes = _load()
    remaining = [n for n in notes if n['id'] != nid]
    if len(remaining) == len(notes):
        return 404, {'error': f'no note with id {nid!r}'}
    _save(remaining)
    return 200, {'id': nid, 'deleted': True}
