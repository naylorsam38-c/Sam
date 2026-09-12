
import json
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "form_builder_and_survey.json"


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

ROUTE = '/api/responses'
METHOD = 'POST'


def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    answer = (body.get('answer') or '').strip()
    if not answer:
        return 400, {'error': 'answer is required'}
    responses = _load()
    next_id = (max([r['id'] for r in responses], default=0)) + 1
    resp = {'id': next_id, 'answer': answer}
    responses.append(resp)
    _save(responses)
    return 201, resp
