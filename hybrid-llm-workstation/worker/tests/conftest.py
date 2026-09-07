from __future__ import annotations

import uuid

import pytest

from workstation_core.config import get_settings
from workstation_core.db import init_db, session_scope
from workstation_core.models_orm import User
from workstation_core.security import hash_password


@pytest.fixture()
def app_env(tmp_path, monkeypatch):
    db_path = tmp_path / f"test-{uuid.uuid4().hex}.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("GPU_PROVIDER", "mock")
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
def owner_user(db):
    user = User(username="sam", password_hash=hash_password("correct-horse-battery-staple"))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture()
def fake_ollama_server():
    from tests.support.fake_ollama import fake_ollama_server as _server

    with _server(["llama3.2:latest"]) as url:
        yield url
