
import importlib.util as _importlib_util
from pathlib import Path as _Path

_shared_lib_path = _Path(__file__).resolve().parents[1] / "CAP-0000" / "shared_lib.py"
_spec = _importlib_util.spec_from_file_location("cap0000_shared_lib", _shared_lib_path)
_shared = _importlib_util.module_from_spec(_spec)
_spec.loader.exec_module(_shared)

DATA_FILE_NAME = "expense_tracker.json"


def _load():
    return _shared.load(DATA_FILE_NAME)


def _save(rows):
    _shared.save(DATA_FILE_NAME, rows)

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
