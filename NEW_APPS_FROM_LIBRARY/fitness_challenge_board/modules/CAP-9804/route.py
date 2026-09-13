
import importlib.util as _importlib_util
from pathlib import Path as _Path

_shared_lib_path = _Path(__file__).resolve().parents[1] / "CAP-0000" / "shared_lib.py"
_spec = _importlib_util.spec_from_file_location("cap0000_shared_lib", _shared_lib_path)
_shared = _importlib_util.module_from_spec(_spec)
_spec.loader.exec_module(_shared)

DATA_FILE_NAME = "fitness_challenge_board.json"


def _load():
    return _shared.load(DATA_FILE_NAME)


def _save(rows):
    _shared.save(DATA_FILE_NAME, rows)

ROUTE = '/api/fitness_challenge_board/buddy_requests'
METHOD = 'POST'


def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    from_id = body.get('requester_id')
    to_id = body.get('target_id')
    if from_id is None or to_id is None:
        return 400, {'error': 'requester_id and target_id are required'}
    positive = bool(body.get('interested', True))
    rows = _load()
    rows.append({'requester_id': from_id, 'target_id': to_id, 'interested': positive})
    _save(rows)
    mutual = any(r['requester_id'] == to_id and r['target_id'] == from_id and r['interested']
                 for r in rows) and positive
    return 200, {'requester_id': from_id, 'target_id': to_id, 'interested': positive, 'paired': mutual}
