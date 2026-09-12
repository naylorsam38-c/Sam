
import json
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "language_learning.json"


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

ROUTE = '/api/cards'
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
