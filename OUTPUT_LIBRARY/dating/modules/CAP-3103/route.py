
import json
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "swipes.json"


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

ROUTE = '/api/swipes'
METHOD = 'POST'


def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    profile_id = body.get('profile_id')
    target_id = body.get('target_id')
    if profile_id is None or target_id is None:
        return 400, {'error': 'profile_id and target_id are required'}
    liked = bool(body.get('liked', True))
    swipes = _load()
    swipes.append({'profile_id': profile_id, 'target_id': target_id, 'liked': liked})
    _save(swipes)
    mutual = any(s['profile_id'] == target_id and s['target_id'] == profile_id and s['liked']
                 for s in swipes) and liked
    return 200, {'profile_id': profile_id, 'target_id': target_id, 'liked': liked, 'match': mutual}
