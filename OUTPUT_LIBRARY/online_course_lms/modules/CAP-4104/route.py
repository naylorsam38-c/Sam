
import json
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "lessons.json"


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

ROUTE = '/api/lessons'
METHOD = 'POST'


def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    course_id = body.get('course_id')
    title = (body.get('title') or '').strip()
    if course_id is None or not title:
        return 400, {'error': 'course_id and title are required'}
    lessons = _load()
    next_id = (max([l['id'] for l in lessons], default=0)) + 1
    lesson = {'id': next_id, 'course_id': course_id, 'title': title}
    lessons.append(lesson)
    _save(lessons)
    return 201, lesson
