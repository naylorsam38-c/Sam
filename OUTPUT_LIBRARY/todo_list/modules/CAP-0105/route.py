
import importlib.util as _importlib_util
from pathlib import Path as _Path

_shared_lib_path = _Path(__file__).resolve().parents[1] / "CAP-0000" / "shared_lib.py"
_spec = _importlib_util.spec_from_file_location("cap0000_shared_lib", _shared_lib_path)
_shared = _importlib_util.module_from_spec(_spec)
_spec.loader.exec_module(_shared)

DATA_FILE_NAME = "todo_list.json"


def _load():
    return _shared.load(DATA_FILE_NAME)


def _save(rows):
    _shared.save(DATA_FILE_NAME, rows)

ROUTE = '/api/todos/delete'
METHOD = 'POST'


def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    todo_id = body.get('id')
    todos = _load()
    remaining = [t for t in todos if t['id'] != todo_id]
    if len(remaining) == len(todos):
        return 404, {'error': f'no todo with id {todo_id!r}'}
    _save(remaining)
    return 200, {'id': todo_id, 'deleted': True}
