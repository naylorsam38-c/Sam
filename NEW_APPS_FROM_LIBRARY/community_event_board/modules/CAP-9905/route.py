
import json
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "notifications.json"


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

ROUTE = '/api/notifications'
METHOD = 'GET'


def handle(request):
    recipient = request.args.get('recipient')
    rows = _load()
    if recipient:
        rows = [r for r in rows if r['recipient'] == recipient]
    return 200, {'notifications': rows}
