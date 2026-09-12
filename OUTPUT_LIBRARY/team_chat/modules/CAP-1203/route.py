
import importlib.util as _importlib_util
from pathlib import Path as _Path

_shared_lib_path = _Path(__file__).resolve().parents[1] / "CAP-0000" / "shared_lib.py"
_spec = _importlib_util.spec_from_file_location("cap0000_shared_lib", _shared_lib_path)
_shared = _importlib_util.module_from_spec(_spec)
_spec.loader.exec_module(_shared)

DATA_FILE_NAME = "team_chat.json"


def _load():
    return _shared.load(DATA_FILE_NAME)


def _save(rows):
    _shared.save(DATA_FILE_NAME, rows)

ROUTE = '/api/team_chat/messages/delete'
METHOD = 'POST'


def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    mid = body.get('id')
    messages = _load()
    remaining = [m for m in messages if m['id'] != mid]
    if len(remaining) == len(messages):
        return 404, {'error': f'no message with id {mid!r}'}
    _save(remaining)
    return 200, {'id': mid, 'deleted': True}
