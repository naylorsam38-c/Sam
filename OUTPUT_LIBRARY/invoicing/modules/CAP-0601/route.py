
import json
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "invoicing.json"


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

ROUTE = '/api/invoices'
METHOD = 'GET'


def handle(request):
    return 200, {'invoices': _load()}
