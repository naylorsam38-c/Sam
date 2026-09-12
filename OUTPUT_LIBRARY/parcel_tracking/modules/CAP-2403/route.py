
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

ROUTE = '/api/parcels/status'
METHOD = 'POST'


def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    pid = body.get('id')
    status = body.get('status') or 'created'
    parcels = _load()
    for p in parcels:
        if p['id'] == pid:
            p['status'] = status
            p.setdefault('history', []).append(status)
            _save(parcels)
            return 200, p
    return 404, {'error': f'no parcel with id {pid!r}'}
