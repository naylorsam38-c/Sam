
import json
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "podcast.json"


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

ROUTE = '/api/episodes/play'
METHOD = 'POST'


def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    eid = body.get('id')
    episodes = _load()
    for e in episodes:
        if e['id'] == eid:
            e['plays'] += 1
            _save(episodes)
            return 200, e
    return 404, {'error': f'no episode with id {eid!r}'}
