
import json
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "appointment_booking.json"


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

ROUTE = '/api/appointments/cancel'
METHOD = 'POST'


def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    aid = body.get('id')
    appts = _load()
    for a in appts:
        if a['id'] == aid:
            a['status'] = 'cancelled'
            _save(appts)
            return 200, a
    return 404, {'error': f'no appointment with id {aid!r}'}
