
import json
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "courses.json"


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

ROUTE = '/api/courses'
METHOD = 'POST'


def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    title = (body.get('title') or '').strip()
    if not title:
        return 400, {'error': 'title is required'}
    courses = _load()
    next_id = (max([c['id'] for c in courses], default=0)) + 1
    course = {'id': next_id, 'title': title}
    courses.append(course)
    _save(courses)
    return 201, course
