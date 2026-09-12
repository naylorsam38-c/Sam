
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

ROUTE = '/api/expenses/total'
METHOD = 'GET'


def handle(request):
    expenses = _load()
    total = sum(x.get('amount', 0) for x in expenses)
    return 200, {'total': total}
