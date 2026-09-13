
import importlib.util as _importlib_util
from pathlib import Path as _Path

_shared_lib_path = _Path(__file__).resolve().parents[1] / "CAP-0000" / "shared_lib.py"
_spec = _importlib_util.spec_from_file_location("cap0000_shared_lib", _shared_lib_path)
_shared = _importlib_util.module_from_spec(_spec)
_spec.loader.exec_module(_shared)

DATA_FILE_NAME = "file_storage_and_sync.json"


def _load():
    return _shared.load(DATA_FILE_NAME)


def _save(rows):
    _shared.save(DATA_FILE_NAME, rows)

ROUTE = '/api/file_storage_and_sync/files/delete'
METHOD = 'POST'


def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    fid = body.get('id')
    files = _load()
    remaining = [f for f in files if f['id'] != fid]
    if len(remaining) == len(files):
        return 404, {'error': f'no file with id {fid!r}'}
    _save(remaining)
    return 200, {'id': fid, 'deleted': True}
