
import importlib.util as _importlib_util
from pathlib import Path as _Path

_shared_lib_path = _Path(__file__).resolve().parents[1] / "CAP-0000" / "shared_lib.py"
_spec = _importlib_util.spec_from_file_location("cap0000_shared_lib", _shared_lib_path)
_shared = _importlib_util.module_from_spec(_spec)
_spec.loader.exec_module(_shared)

DATA_FILE_NAME = "spreadsheet.json"


def _load():
    return _shared.load(DATA_FILE_NAME)


def _save(rows):
    _shared.save(DATA_FILE_NAME, rows)

ROUTE = '/api/spreadsheet/cells/set'
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
