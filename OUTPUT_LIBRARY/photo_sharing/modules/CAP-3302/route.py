
import importlib.util as _importlib_util
from pathlib import Path as _Path

_shared_lib_path = _Path(__file__).resolve().parents[1] / "CAP-0000" / "shared_lib.py"
_spec = _importlib_util.spec_from_file_location("cap0000_shared_lib", _shared_lib_path)
_shared = _importlib_util.module_from_spec(_spec)
_spec.loader.exec_module(_shared)

DATA_FILE_NAME = "photo_sharing.json"


def _load():
    return _shared.load(DATA_FILE_NAME)


def _save(rows):
    _shared.save(DATA_FILE_NAME, rows)

ROUTE = '/api/photos'
METHOD = 'POST'


PLACEHOLDER_PNG_B64 = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII='
def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    caption = (body.get('caption') or '').strip()
    if not caption:
        return 400, {'error': 'caption is required'}
    photos = _load()
    next_id = (max([p['id'] for p in photos], default=0)) + 1
    photo = {'id': next_id, 'caption': caption, 'image_b64': PLACEHOLDER_PNG_B64, 'likes': 0}
    photos.append(photo)
    _save(photos)
    return 201, photo
