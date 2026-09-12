
import json
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "photo_sharing.json"


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
