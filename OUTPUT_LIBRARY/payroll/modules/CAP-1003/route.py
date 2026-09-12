
import importlib.util as _importlib_util
from pathlib import Path as _Path

_shared_lib_path = _Path(__file__).resolve().parents[1] / "CAP-0000" / "shared_lib.py"
_spec = _importlib_util.spec_from_file_location("cap0000_shared_lib", _shared_lib_path)
_shared = _importlib_util.module_from_spec(_spec)
_spec.loader.exec_module(_shared)

DATA_FILE_NAME = "pay_records.json"


def _load():
    return _shared.load(DATA_FILE_NAME)


def _save(rows):
    _shared.save(DATA_FILE_NAME, rows)

ROUTE = '/api/payroll/run'
METHOD = 'POST'


def handle(request):
    employees = _shared.load('employees.json')
    records = _load()
    next_id = (max([r['id'] for r in records], default=0))
    created = 0
    for e in employees:
        next_id += 1
        gross = e.get('salary', 0)
        net = round(gross * 0.8, 2)
        records.append({'id': next_id, 'employee_id': e['id'], 'gross': gross, 'net': net})
        created += 1
    _save(records)
    return 200, {'created': created}
