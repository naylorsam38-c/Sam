
import json
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "meal_plan.json"


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

ROUTE = '/api/meal_plan'
METHOD = 'POST'


def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    day = (body.get('day') or '').strip()
    recipe_id = body.get('recipe_id')
    if not day or recipe_id is None:
        return 400, {'error': 'day and recipe_id are required'}
    plan = _load()
    plan = [p for p in plan if p['day'] != day]
    entry = {'day': day, 'recipe_id': recipe_id}
    plan.append(entry)
    _save(plan)
    return 201, entry
