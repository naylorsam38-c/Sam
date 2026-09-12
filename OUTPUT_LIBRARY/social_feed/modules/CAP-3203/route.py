
import json
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "social_feed.json"


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

ROUTE = '/api/posts/like'
METHOD = 'POST'


def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    pid = body.get('id')
    posts = _load()
    for p in posts:
        if p['id'] == pid:
            p['likes'] += 1
            _save(posts)
            return 200, p
    return 404, {'error': f'no post with id {pid!r}'}
