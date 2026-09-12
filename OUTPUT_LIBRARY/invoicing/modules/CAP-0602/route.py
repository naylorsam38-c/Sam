
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
METHOD = 'POST'


def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    client = (body.get('client') or '').strip()
    if not client:
        return 400, {'error': 'client is required'}
    try:
        amount = float(body.get('amount', 0) or 0)
    except (TypeError, ValueError):
        amount = 0.0
    invoices = _load()
    next_id = (max([i['id'] for i in invoices], default=0)) + 1
    inv = {'id': next_id, 'client': client, 'amount': amount, 'status': 'draft'}
    invoices.append(inv)
    _save(invoices)
    return 201, inv
