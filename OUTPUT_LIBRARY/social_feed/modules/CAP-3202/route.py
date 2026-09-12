
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
