
import json
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "accounting_ledger.json"


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

ROUTE = '/api/entries/delete'
METHOD = 'POST'


def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    eid = body.get('id')
    entries = _load()
    remaining = [e for e in entries if e['id'] != eid]
    if len(remaining) == len(entries):
        return 404, {'error': f'no entry with id {eid!r}'}
    _save(remaining)
    return 200, {'id': eid, 'deleted': True}
