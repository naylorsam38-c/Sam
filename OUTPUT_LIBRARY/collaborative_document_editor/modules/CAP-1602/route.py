
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

ROUTE = '/api/docs'
METHOD = 'POST'


def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    title = (body.get('title') or '').strip()
    if not title:
        return 400, {'error': 'title is required'}
    docs = _load()
    next_id = (max([d['id'] for d in docs], default=0)) + 1
    doc = {'id': next_id, 'title': title, 'content': ''}
    docs.append(doc)
    _save(docs)
    return 201, doc
