
import importlib.util as _importlib_util
from pathlib import Path as _Path

_shared_lib_path = _Path(__file__).resolve().parents[1] / "CAP-0000" / "shared_lib.py"
_spec = _importlib_util.spec_from_file_location("cap0000_shared_lib", _shared_lib_path)
_shared = _importlib_util.module_from_spec(_spec)
_spec.loader.exec_module(_shared)

DATA_FILE_NAME = "swipes.json"


def _load():
    return _shared.load(DATA_FILE_NAME)


def _save(rows):
    _shared.save(DATA_FILE_NAME, rows)

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
