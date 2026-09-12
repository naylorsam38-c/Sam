
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

ROUTE = '/api/expense_tracker/expenses/delete'
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
