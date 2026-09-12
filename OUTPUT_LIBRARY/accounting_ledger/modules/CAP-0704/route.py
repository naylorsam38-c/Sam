
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

ROUTE = '/api/entries/balance'
METHOD = 'GET'


def handle(request):
    entries = _load()
    credit = sum(e.get('amount', 0) for e in entries if e.get('type') == 'credit')
    debit = sum(e.get('amount', 0) for e in entries if e.get('type') == 'debit')
    return 200, {'balance': credit - debit}
