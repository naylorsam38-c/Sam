
import json
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "expense_tracker.json"


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

ROUTE = '/api/expenses/delete'
METHOD = 'POST'


def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    xid = body.get('id')
    expenses = _load()
    remaining = [x for x in expenses if x['id'] != xid]
    if len(remaining) == len(expenses):
        return 404, {'error': f'no expense with id {xid!r}'}
    _save(remaining)
    return 200, {'id': xid, 'deleted': True}
