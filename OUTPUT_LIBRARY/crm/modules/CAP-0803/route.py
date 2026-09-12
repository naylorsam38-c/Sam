
import json
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "crm.json"


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

ROUTE = '/api/contacts/stage'
METHOD = 'POST'


def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    cid = body.get('id')
    stage = body.get('stage') or 'lead'
    contacts = _load()
    for c in contacts:
        if c['id'] == cid:
            c['stage'] = stage
            _save(contacts)
            return 200, c
    return 404, {'error': f'no contact with id {cid!r}'}
