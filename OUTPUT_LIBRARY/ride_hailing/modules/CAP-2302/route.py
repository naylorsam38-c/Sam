
import json
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "ride_hailing.json"


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

ROUTE = '/api/rides'
METHOD = 'POST'


def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    pickup = (body.get('pickup') or '').strip()
    if not pickup:
        return 400, {'error': 'pickup is required'}
    dropoff = body.get('dropoff') or ''
    rides = _load()
    next_id = (max([r['id'] for r in rides], default=0)) + 1
    ride = {'id': next_id, 'pickup': pickup, 'dropoff': dropoff, 'status': 'requested'}
    rides.append(ride)
    _save(rides)
    return 201, ride
