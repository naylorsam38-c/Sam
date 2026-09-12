
import importlib.util as _importlib_util
from pathlib import Path as _Path

_shared_lib_path = _Path(__file__).resolve().parents[1] / "CAP-0000" / "shared_lib.py"
_spec = _importlib_util.spec_from_file_location("cap0000_shared_lib", _shared_lib_path)
_shared = _importlib_util.module_from_spec(_spec)
_spec.loader.exec_module(_shared)

DATA_FILE_NAME = "invoicing.json"


def _load():
    return _shared.load(DATA_FILE_NAME)


def _save(rows):
    _shared.save(DATA_FILE_NAME, rows)

ROUTE = '/api/invoices'
METHOD = 'POST'


def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    client = (body.get('client') or '').strip()
    if not client:
        return 400, {'error': 'client is required'}
    try:
        amount = float(body.get('amount', 0) or 0)
    except (TypeError, ValueError):
        amount = 0.0
    invoices = _load()
    next_id = (max([i['id'] for i in invoices], default=0)) + 1
    inv = {'id': next_id, 'client': client, 'amount': amount, 'status': 'draft'}
    invoices.append(inv)
    _save(invoices)
    return 201, inv
