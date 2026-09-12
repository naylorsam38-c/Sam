
import json
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "fleet_tracking.json"


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

ROUTE = '/api/vehicles'
METHOD = 'POST'


def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    name = (body.get('name') or '').strip()
    if not name:
        return 400, {'error': 'name is required'}
    vehicles = _load()
    next_id = (max([v['id'] for v in vehicles], default=0)) + 1
    vehicle = {'id': next_id, 'name': name, 'status': 'idle', 'location': ''}
    vehicles.append(vehicle)
    _save(vehicles)
    return 201, vehicle
