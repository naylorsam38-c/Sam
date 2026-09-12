
import json
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "profiles.json"


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

ROUTE = '/api/profiles'
METHOD = 'POST'


def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    name = (body.get('name') or '').strip()
    if not name:
        return 400, {'error': 'name is required'}
    bio = body.get('bio') or ''
    profiles = _load()
    next_id = (max([p['id'] for p in profiles], default=0)) + 1
    profile = {'id': next_id, 'name': name, 'bio': bio}
    profiles.append(profile)
    _save(profiles)
    return 201, profile
