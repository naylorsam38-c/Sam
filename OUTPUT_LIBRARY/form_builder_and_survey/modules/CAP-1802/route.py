
import importlib.util as _importlib_util
from pathlib import Path as _Path

_shared_lib_path = _Path(__file__).resolve().parents[1] / "CAP-0000" / "shared_lib.py"
_spec = _importlib_util.spec_from_file_location("cap0000_shared_lib", _shared_lib_path)
_shared = _importlib_util.module_from_spec(_spec)
_spec.loader.exec_module(_shared)

DATA_FILE_NAME = "form_builder_and_survey.json"


def _load():
    return _shared.load(DATA_FILE_NAME)


def _save(rows):
    _shared.save(DATA_FILE_NAME, rows)

ROUTE = '/api/form_builder_and_survey/responses'
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
