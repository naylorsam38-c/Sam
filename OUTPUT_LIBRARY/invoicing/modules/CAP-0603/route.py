
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

ROUTE = '/api/invoices/pay'
METHOD = 'POST'


def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    iid = body.get('id')
    invoices = _load()
    for i in invoices:
        if i['id'] == iid:
            i['status'] = 'paid'
            _save(invoices)
            return 200, i
    return 404, {'error': f'no invoice with id {iid!r}'}
