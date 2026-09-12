
import json
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "short_video_feed.json"


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

ROUTE = '/api/videos'
METHOD = 'POST'


def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    caption = (body.get('caption') or '').strip()
    if not caption:
        return 400, {'error': 'caption is required'}
    videos = _load()
    next_id = (max([v['id'] for v in videos], default=0)) + 1
    video = {'id': next_id, 'caption': caption, 'views': 0, 'likes': 0}
    videos.append(video)
    _save(videos)
    return 201, video
