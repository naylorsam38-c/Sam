
import importlib.util as _importlib_util
from pathlib import Path as _Path

_shared_lib_path = _Path(__file__).resolve().parents[1] / "CAP-0000" / "shared_lib.py"
_spec = _importlib_util.spec_from_file_location("cap0000_shared_lib", _shared_lib_path)
_shared = _importlib_util.module_from_spec(_spec)
_spec.loader.exec_module(_shared)

DATA_FILE_NAME = "accounting_ledger.json"


def _load():
    return _shared.load(DATA_FILE_NAME)


def _save(rows):
    _shared.save(DATA_FILE_NAME, rows)

ROUTE = '/api/entries/balance'
METHOD = 'GET'


def handle(request):
    entries = _load()
    credit = sum(e.get('amount', 0) for e in entries if e.get('type') == 'credit')
    debit = sum(e.get('amount', 0) for e in entries if e.get('type') == 'debit')
    return 200, {'balance': credit - debit}
