
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

ROUTE = '/api/notes'
METHOD = 'POST'


def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    title = (body.get('title') or '').strip()
    text = (body.get('body') or '').strip()
    if not title:
        return 400, {'error': 'title is required'}
    notes = _load()
    next_id = (max([n['id'] for n in notes], default=0)) + 1
    note = {'id': next_id, 'title': title, 'body': text}
    notes.append(note)
    _save(notes)
    return 201, note
