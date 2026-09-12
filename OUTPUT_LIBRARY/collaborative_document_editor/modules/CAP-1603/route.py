
import json
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "collaborative_document_editor.json"


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

ROUTE = '/api/docs/update'
METHOD = 'POST'


def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    did = body.get('id')
    content = body.get('content', '')
    docs = _load()
    for d in docs:
        if d['id'] == did:
            d['content'] = content
            _save(docs)
            return 200, d
    return 404, {'error': f'no doc with id {did!r}'}
