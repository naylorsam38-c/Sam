
import json
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "spreadsheet.json"


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

ROUTE = '/api/cells/set'
METHOD = 'POST'


def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    row = body.get('row')
    col = body.get('col')
    if row is None or col is None:
        return 400, {'error': 'row and col are required'}
    value = body.get('value', '')
    cells = _load()
    for c in cells:
        if c['row'] == row and c['col'] == col:
            c['value'] = value
            _save(cells)
            return 200, c
    cell = {'row': row, 'col': col, 'value': value}
    cells.append(cell)
    _save(cells)
    return 201, cell
