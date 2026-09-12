
import json
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "video_conferencing.json"


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

ROUTE = '/api/rooms/join'
METHOD = 'POST'


def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    rid = body.get('id')
    participant = (body.get('participant') or '').strip()
    if rid is None or not participant:
        return 400, {'error': 'id and participant are required'}
    rooms = _load()
    for r in rooms:
        if r['id'] == rid:
            if participant not in r['participants']:
                r['participants'].append(participant)
            _save(rooms)
            return 200, r
    return 404, {'error': f'no room with id {rid!r}'}
