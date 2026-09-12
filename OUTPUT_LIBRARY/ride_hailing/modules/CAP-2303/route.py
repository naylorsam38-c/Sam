
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

ROUTE = '/api/rides/status'
METHOD = 'POST'


def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    rid = body.get('id')
    status = body.get('status') or 'requested'
    rides = _load()
    for r in rides:
        if r['id'] == rid:
            r['status'] = status
            _save(rides)
            return 200, r
    return 404, {'error': f'no ride with id {rid!r}'}
