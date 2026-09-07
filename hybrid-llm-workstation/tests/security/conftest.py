"""Reuses the control API's fixtures for security-focused tests — same
running app, different lens (attack surface rather than feature behavior).

Loaded via importlib under a distinct module name (not the literal name
"conftest") to avoid colliding with pytest's own per-directory conftest.py
module registry, then re-exposed here by direct assignment so pytest's
fixture discovery (which scans this module's own namespace) picks them up.
"""

import importlib.util
from pathlib import Path

_SOURCE_PATH = Path(__file__).resolve().parents[2] / "apps" / "control" / "tests" / "conftest.py"
_spec = importlib.util.spec_from_file_location("control_tests_conftest", _SOURCE_PATH)
_control_conftest = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_control_conftest)

app_env = _control_conftest.app_env
db = _control_conftest.db
test_user = _control_conftest.test_user
client = _control_conftest.client
fake_ollama_server = _control_conftest.fake_ollama_server
auth_headers = _control_conftest.auth_headers
