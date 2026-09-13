
import importlib.util as _importlib_util
from pathlib import Path as _Path

_shared_lib_path = _Path(__file__).resolve().parents[1] / "CAP-0000" / "shared_lib.py"
_spec = _importlib_util.spec_from_file_location("cap0000_shared_lib", _shared_lib_path)
_shared = _importlib_util.module_from_spec(_spec)
_spec.loader.exec_module(_shared)

DATA_FILE_NAME = "language_learning.json"


def _load():
    return _shared.load(DATA_FILE_NAME)


def _save(rows):
    _shared.save(DATA_FILE_NAME, rows)

ROUTE = '/api/language_learning/cards'
METHOD = 'POST'


def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    front = (body.get('front') or '').strip()
    if not front:
        return 400, {'error': 'front is required'}
    back = body.get('back') or ''
    cards = _load()
    next_id = (max([c['id'] for c in cards], default=0)) + 1
    card = {'id': next_id, 'front': front, 'back': back, 'correct': 0, 'incorrect': 0}
    cards.append(card)
    _save(cards)
    return 201, card
