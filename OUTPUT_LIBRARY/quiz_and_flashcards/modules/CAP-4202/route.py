
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

ROUTE = '/api/cards'
METHOD = 'POST'


def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    question = (body.get('question') or '').strip()
    if not question:
        return 400, {'error': 'question is required'}
    answer = body.get('answer') or ''
    cards = _load()
    next_id = (max([c['id'] for c in cards], default=0)) + 1
    card = {'id': next_id, 'question': question, 'answer': answer, 'correct_count': 0}
    cards.append(card)
    _save(cards)
    return 201, card
