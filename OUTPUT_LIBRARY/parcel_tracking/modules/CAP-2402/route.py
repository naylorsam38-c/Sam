
import json
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "parcel_tracking.json"


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

ROUTE = '/api/parcels'
METHOD = 'POST'


def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    tracking_no = (body.get('tracking_no') or '').strip()
    if not tracking_no:
        return 400, {'error': 'tracking_no is required'}
    parcels = _load()
    next_id = (max([p['id'] for p in parcels], default=0)) + 1
    parcel = {'id': next_id, 'tracking_no': tracking_no, 'status': 'created', 'history': ['created']}
    parcels.append(parcel)
    _save(parcels)
    return 201, parcel
