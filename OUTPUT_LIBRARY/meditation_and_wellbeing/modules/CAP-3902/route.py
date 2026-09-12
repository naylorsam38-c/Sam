
import json
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "meditation_and_wellbeing.json"


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

ROUTE = '/api/sessions'
METHOD = 'POST'


def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    stype = (body.get('type') or '').strip()
    if not stype:
        return 400, {'error': 'type is required'}
    try:
        duration = float(body.get('duration', 0) or 0)
    except (TypeError, ValueError):
        duration = 0.0
    sessions = _load()
    next_id = (max([s['id'] for s in sessions], default=0)) + 1
    session = {'id': next_id, 'type': stype, 'duration': duration}
    sessions.append(session)
    _save(sessions)
    return 201, session
