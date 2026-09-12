
import json
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "quiz_and_flashcards.json"


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

ROUTE = '/api/cards/review'
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
