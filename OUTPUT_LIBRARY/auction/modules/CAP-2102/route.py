
import importlib.util as _importlib_util
from pathlib import Path as _Path

_shared_lib_path = _Path(__file__).resolve().parents[1] / "CAP-0000" / "shared_lib.py"
_spec = _importlib_util.spec_from_file_location("cap0000_shared_lib", _shared_lib_path)
_shared = _importlib_util.module_from_spec(_spec)
_spec.loader.exec_module(_shared)

DATA_FILE_NAME = "auction.json"


def _load():
    return _shared.load(DATA_FILE_NAME)


def _save(rows):
    _shared.save(DATA_FILE_NAME, rows)

ROUTE = '/api/auction/items'
METHOD = 'POST'


def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    title = (body.get('title') or '').strip()
    if not title:
        return 400, {'error': 'title is required'}
    try:
        starting_bid = float(body.get('starting_bid', 0) or 0)
    except (TypeError, ValueError):
        starting_bid = 0.0
    items = _load()
    next_id = (max([i['id'] for i in items], default=0)) + 1
    item = {'id': next_id, 'title': title, 'current_bid': starting_bid, 'highest_bidder': None}
    items.append(item)
    _save(items)
    return 201, item
