
import importlib.util as _importlib_util
from pathlib import Path as _Path

_shared_lib_path = _Path(__file__).resolve().parents[1] / "CAP-0000" / "shared_lib.py"
_spec = _importlib_util.spec_from_file_location("cap0000_shared_lib", _shared_lib_path)
_shared = _importlib_util.module_from_spec(_spec)
_spec.loader.exec_module(_shared)

DATA_FILE_NAME = "users.json"


def _load():
    return _shared.load(DATA_FILE_NAME)


def _save(rows):
    _shared.save(DATA_FILE_NAME, rows)

ROUTE = '/api/note_taking/auth/login'
METHOD = 'POST'


def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    email = (body.get('email') or '').strip().lower()
    password = body.get('password') or ''
    users = _load()
    for user in users:
        if user['email'] == email and _shared.verify_password(password, user['password_hash']):
            token = _shared.create_session(user['id'], extra={'role': user.get('role')}, ttl_minutes=720, role_source=('users.json', 'id'))
            _shared.audit(email, 'login_success', 'users.json', user['id'])
            return 200, {'token': token, 'user_id': user['id'], 'role': user.get('role')}
    _shared.audit(email, 'login_failure', 'users.json', None, 'invalid credentials -- actor is the CLAIMED email, not a verified identity')
    return 401, {'error': 'invalid email or password'}
