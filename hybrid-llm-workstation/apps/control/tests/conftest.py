from __future__ import annotations

import os
import uuid

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("GPU_PROVIDER", "mock")
os.environ.setdefault("GPU_IDLE_TIMEOUT_MINUTES", "20")
os.environ.setdefault("GPU_MONITOR_INTERVAL_SECONDS", "3600")  # tests trigger ticks manually

from workstation_core.config import get_settings  # noqa: E402
from workstation_core.db import init_db, session_scope  # noqa: E402
from workstation_core.models_orm import Base, User  # noqa: E402
from workstation_core.security import hash_password  # noqa: E402


@pytest.fixture()
def app_env(tmp_path, monkeypatch):
    # Settings reads a real .env file relative to the process CWD if one
    # exists there (e.g. a developer's own local dev config). Explicitly
    # pin every externally-reachable setting to a safe, deterministic test
    # value so the suite can never accidentally pass (or fail) because of
    # whatever happens to be running on the machine outside the tests.
    monkeypatch.setenv("OLLAMA_LOCAL_URL", "http://127.0.0.1:1")  # nothing listens here
    monkeypatch.setenv("CLOUD_LLM_BASE_URL", "")
    monkeypatch.setenv("EXECUTION_AGENT_URL", "http://127.0.0.1:1")
    monkeypatch.setenv("EXECUTION_AGENT_TOKEN", "test-execution-agent-token")
    monkeypatch.setenv("GPU_PROVIDER_API_KEY", "")
    monkeypatch.setenv("GPU_TEMPLATE_ID", "")
    monkeypatch.setenv("GPU_VOLUME_ID", "")
    monkeypatch.setenv("OPEN_WEBUI_PROXY_TOKEN", "")

    db_path = tmp_path / f"test-{uuid.uuid4().hex}.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    get_settings.cache_clear()
    settings = get_settings()
    engine = init_db(settings.database_url, create_all=True)
    yield settings
    engine.dispose()


@pytest.fixture()
def db(app_env):
    with session_scope() as session:
        yield session


@pytest.fixture()
def test_user(db):
    user = User(username="sam", password_hash=hash_password("correct-horse-battery-staple"))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture()
def client(app_env):
    from control.main import create_app

    app = create_app()
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def fake_ollama_server():
    from tests.support.fake_ollama import fake_ollama_server as _server

    with _server(["llama3.2:latest"]) as url:
        yield url


@pytest.fixture()
def auth_headers(client, test_user):
    resp = client.post("/api/auth/login", json={"username": "sam", "password": "correct-horse-battery-staple"})
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
