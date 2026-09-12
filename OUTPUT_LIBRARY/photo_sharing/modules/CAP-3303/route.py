
import json
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "photo_sharing.json"


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

ROUTE = '/api/photos/like'
METHOD = 'POST'


def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    pid = body.get('id')
    photos = _load()
    for p in photos:
        if p['id'] == pid:
            p['likes'] += 1
            _save(photos)
            return 200, p
    return 404, {'error': f'no photo with id {pid!r}'}
