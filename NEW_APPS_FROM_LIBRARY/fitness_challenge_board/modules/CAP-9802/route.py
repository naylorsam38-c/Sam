
import importlib.util as _importlib_util
from pathlib import Path as _Path

_shared_lib_path = _Path(__file__).resolve().parents[1] / "CAP-0000" / "shared_lib.py"
_spec = _importlib_util.spec_from_file_location("cap0000_shared_lib", _shared_lib_path)
_shared = _importlib_util.module_from_spec(_spec)
_spec.loader.exec_module(_shared)

DATA_FILE_NAME = "challenges.json"


def _load():
    return _shared.load(DATA_FILE_NAME)


def _save(rows):
    _shared.save(DATA_FILE_NAME, rows)

ROUTE = '/api/challenges'
METHOD = 'POST'


def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    title = (body.get('title') or '').strip()
    if not title:
        return 400, {'error': 'title is required'}
    try:
        max_participants = int(body.get('max_participants', 4) or 4)
    except (TypeError, ValueError):
        max_participants = 4
    challenges = _load()
    next_id = (max([c['id'] for c in challenges], default=0)) + 1
    ch = {'id': next_id, 'title': title, 'max_participants': max_participants, 'participants': 0}
    challenges.append(ch)
    _save(challenges)
    return 201, ch
