
import json
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "video_streaming.json"


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

ROUTE = '/api/videos/watch'
METHOD = 'POST'


def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    vid = body.get('id')
    videos = _load()
    for v in videos:
        if v['id'] == vid:
            v['views'] += 1
            _save(videos)
            return 200, v
    return 404, {'error': f'no video with id {vid!r}'}
