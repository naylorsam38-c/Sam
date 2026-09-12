
import importlib.util as _importlib_util
from pathlib import Path as _Path

_shared_lib_path = _Path(__file__).resolve().parents[1] / "CAP-0000" / "shared_lib.py"
_spec = _importlib_util.spec_from_file_location("cap0000_shared_lib", _shared_lib_path)
_shared = _importlib_util.module_from_spec(_spec)
_spec.loader.exec_module(_shared)

DATA_FILE_NAME = "note_taking.json"


def _load():
    return _shared.load(DATA_FILE_NAME)


def _save(rows):
    _shared.save(DATA_FILE_NAME, rows)

ROUTE = '/api/note_taking/notes/update'
METHOD = 'POST'


def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    nid = body.get('id')
    notes = _load()
    for n in notes:
        if n['id'] == nid:
            n['title'] = (body.get('title') or n['title']).strip()
            n['body'] = body.get('body', n['body'])
            _save(notes)
            return 200, n
    return 404, {'error': f'no note with id {nid!r}'}
