
import importlib.util as _importlib_util
from pathlib import Path as _Path

_shared_lib_path = _Path(__file__).resolve().parents[1] / "CAP-0000" / "shared_lib.py"
_spec = _importlib_util.spec_from_file_location("cap0000_shared_lib", _shared_lib_path)
_shared = _importlib_util.module_from_spec(_spec)
_spec.loader.exec_module(_shared)

DATA_FILE_NAME = "users.json"


def _load():
    return _shared.load(DATA_FILE_NAME)


def _save(rows):
    _shared.save(DATA_FILE_NAME, rows)

ROUTE = '/api/note_taking/auth/logout'
METHOD = 'POST'


def handle(request, ctx):
    if not ctx.get('authenticated'):
        return 401, {'error': 'not authenticated'}
    _shared.invalidate_session(ctx['token'])
    _shared.audit(ctx['user'], 'logout', 'users.json', ctx['user'])
    return 200, {'logged_out': True}
