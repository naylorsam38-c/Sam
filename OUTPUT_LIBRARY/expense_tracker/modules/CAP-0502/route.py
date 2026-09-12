
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

ROUTE = '/api/expenses'
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
    category = body.get('category') or 'general'
    expenses = _load()
    next_id = (max([x['id'] for x in expenses], default=0)) + 1
    exp = {'id': next_id, 'description': description, 'amount': amount, 'category': category}
    expenses.append(exp)
    _save(expenses)
    return 201, exp
