
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

ROUTE = '/api/entries'
METHOD = 'POST'


def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    description = (body.get('description') or '').strip()
    if not description:
        return 400, {'error': 'description is required'}
    try:
        amount = float(body.get('amount', 0) or 0)
    except (TypeError, ValueError):
        amount = 0.0
    entry_type = body.get('type') if body.get('type') in ('debit', 'credit') else 'debit'
    entries = _load()
    next_id = (max([e['id'] for e in entries], default=0)) + 1
    entry = {'id': next_id, 'description': description, 'amount': amount, 'type': entry_type}
    entries.append(entry)
    _save(entries)
    return 201, entry
