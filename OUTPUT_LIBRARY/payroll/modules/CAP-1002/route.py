
import json
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "employees.json"


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

ROUTE = '/api/employees'
METHOD = 'POST'


def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    name = (body.get('name') or '').strip()
    if not name:
        return 400, {'error': 'name is required'}
    try:
        salary = float(body.get('salary', 0) or 0)
    except (TypeError, ValueError):
        salary = 0.0
    employees = _load()
    next_id = (max([e['id'] for e in employees], default=0)) + 1
    emp = {'id': next_id, 'name': name, 'salary': salary}
    employees.append(emp)
    _save(employees)
    return 201, emp
