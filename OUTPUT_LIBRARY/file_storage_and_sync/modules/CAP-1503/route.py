
import json
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "file_storage_and_sync.json"


def _load():
    if not DATA_FILE.is_file():
        return []
    try:
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save(rows):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(rows), encoding="utf-8")

ROUTE = '/api/files/delete'
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
