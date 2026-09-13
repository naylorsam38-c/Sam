
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

ROUTE = '/api/note_taking/auth/bootstrap-admin'
METHOD = 'POST'


def handle(request):
    body = request.get_json(force=True, silent=True) or {}
    email = (body.get('email') or '').strip().lower()
    password = body.get('password') or ''
    if not email or not password:
        return 400, {'error': 'email and password are required'}
    if len(password) < 8:
        return 400, {'error': 'password must be at least 8 characters'}
    if _shared.is_common_password(password):
        return 400, {'error': 'this password is too common; choose a less predictable one'}
    users = _load()
    if any(u.get('role') == 'admin' for u in users):
        return 403, {'error': 'an admin account already exists; ask an admin to create your account'}
    if any(u['email'] == email for u in users):
        return 409, {'error': 'an account with this email already exists'}
    next_id = (max([u['id'] for u in users], default=0)) + 1
    user = {'id': next_id, 'email': email, 'password_hash': _shared.hash_password(password), 'role': 'admin'}
    users.append(user)
    _save(users)
    _shared.audit(email, 'bootstrap_admin', 'users.json', next_id, 'first admin account for this instance')
    return 201, {k: v for k, v in user.items() if k != 'password_hash'}
