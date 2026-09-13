
import importlib.util as _importlib_util
from pathlib import Path as _Path

_shared_lib_path = _Path(__file__).resolve().parents[1] / "CAP-0000" / "shared_lib.py"
_spec = _importlib_util.spec_from_file_location("cap0000_shared_lib", _shared_lib_path)
_shared = _importlib_util.module_from_spec(_spec)
_spec.loader.exec_module(_shared)

DATA_FILE_NAME = "quiz_and_flashcards.json"


def _load():
    return _shared.load(DATA_FILE_NAME)


def _save(rows):
    _shared.save(DATA_FILE_NAME, rows)

ROUTE = '/api/quiz_and_flashcards/cards/review'
METHOD = 'POST'


def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    cid = body.get('id')
    correct = bool(body.get('correct', False))
    cards = _load()
    for c in cards:
        if c['id'] == cid:
            if correct:
                c['correct_count'] += 1
            _save(cards)
            return 200, c
    return 404, {'error': f'no card with id {cid!r}'}
