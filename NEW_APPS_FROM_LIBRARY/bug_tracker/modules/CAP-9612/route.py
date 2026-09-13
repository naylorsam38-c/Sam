
import importlib.util as _importlib_util
from pathlib import Path as _Path

_shared_lib_path = _Path(__file__).resolve().parents[1] / "CAP-0000" / "shared_lib.py"
_spec = _importlib_util.spec_from_file_location("cap0000_shared_lib", _shared_lib_path)
_shared = _importlib_util.module_from_spec(_spec)
_spec.loader.exec_module(_shared)

DATA_FILE_NAME = "bug_tracker.json"


def _load():
    return _shared.load(DATA_FILE_NAME)


def _save(rows):
    _shared.save(DATA_FILE_NAME, rows)

ROUTE = '/api/bug_tracker/bugs'
METHOD = 'POST'


def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    title = (body.get('title') or '').strip()
    if not title:
        return 400, {'error': 'title is required'}
    bugs = _load()
    next_id = (max([b['id'] for b in bugs], default=0)) + 1
    bug = {'id': next_id, 'title': title, 'status': 'open'}
    bugs.append(bug)
    _save(bugs)
    return 201, bug
