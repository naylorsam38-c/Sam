
import json
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "pay_records.json"


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

ROUTE = '/api/payroll/run'
METHOD = 'POST'


import json
from pathlib import Path
EMP_FILE = Path(__file__).resolve().parents[2] / 'data' / 'employees.json'
def _load_employees():
    if not EMP_FILE.is_file():
        return []
    try:
        return json.loads(EMP_FILE.read_text(encoding='utf-8'))
    except Exception:
        return []
def handle(request):
    employees = _load_employees()
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
