
import importlib.util as _importlib_util
from pathlib import Path as _Path

_shared_lib_path = _Path(__file__).resolve().parents[1] / "CAP-0000" / "shared_lib.py"
_spec = _importlib_util.spec_from_file_location("cap0000_shared_lib", _shared_lib_path)
_shared = _importlib_util.module_from_spec(_spec)
_spec.loader.exec_module(_shared)

DATA_FILE_NAME = "social_feed.json"


def _load():
    return _shared.load(DATA_FILE_NAME)


def _save(rows):
    _shared.save(DATA_FILE_NAME, rows)

ROUTE = '/api/posts'
METHOD = 'POST'


def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    text = (body.get('text') or '').strip()
    if not text:
        return 400, {'error': 'text is required'}
    posts = _load()
    next_id = (max([p['id'] for p in posts], default=0)) + 1
    post = {'id': next_id, 'author': 'You', 'text': text, 'likes': 0}
    posts.append(post)
    _save(posts)
    return 201, post
