
import importlib.util as _importlib_util
from pathlib import Path as _Path

_shared_lib_path = _Path(__file__).resolve().parents[1] / "CAP-0000" / "shared_lib.py"
_spec = _importlib_util.spec_from_file_location("cap0000_shared_lib", _shared_lib_path)
_shared = _importlib_util.module_from_spec(_spec)
_spec.loader.exec_module(_shared)

DATA_FILE_NAME = "lessons.json"


def _load():
    return _shared.load(DATA_FILE_NAME)


def _save(rows):
    _shared.save(DATA_FILE_NAME, rows)

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
