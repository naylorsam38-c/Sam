"""Shared fixtures for e2e/acceptance tests: a real control API (uvicorn),
a real local execution agent (uvicorn), and a real fake-Ollama server, all
on real sockets — only the cloud GPU and the laptop's actual Ollama
installation are stood in for (by the mock provider and the fake server,
respectively), because this build environment has neither.
"""

from __future__ import annotations

import socket
import threading
import time
import uuid

import httpx
import pytest
import uvicorn
import yaml

from agent.config import AgentSettings
from agent.main import create_app as create_agent_app
from workstation_core.config import get_settings
from workstation_core.db import init_db, session_scope
from workstation_core.models_orm import User
from workstation_core.security import hash_password

SHARED_AGENT_TOKEN = "e2e-shared-secret"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture()
def workspace(tmp_path):
    ws = tmp_path / "workstation-workspace"
    ws.mkdir()
    return ws


@pytest.fixture()
def policies_file(tmp_path, workspace):
    path = tmp_path / "policies.yaml"
    path.write_text(yaml.safe_dump({
        "operations": [
            {"operation": "read_file", "level": "APPROVAL", "risk": "LOW", "allowed_paths": [str(workspace)]},
            {"operation": "run_command", "level": "APPROVAL", "risk": "MEDIUM", "allowed_paths": [str(workspace)],
             "allowed_commands": ["python3"]},
        ]
    }))
    return path


@pytest.fixture()
def fake_ollama_server():
    from tests.support.fake_ollama import fake_ollama_server as _server

    with _server(["llama3.2:latest"]) as url:
        yield url


@pytest.fixture()
def running_agent(policies_file, tmp_path):
    settings = AgentSettings(
        execution_agent_token=SHARED_AGENT_TOKEN, policies_path=policies_file,
        audit_db_path=tmp_path / "agent-audit.db", command_timeout_seconds=15,
    )
    port = _free_port()
    config = uvicorn.Config(create_agent_app(settings), host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    base_url = f"http://127.0.0.1:{port}"
    deadline = time.time() + 10
    while time.time() < deadline:
        try:
            httpx.get(f"{base_url}/health", timeout=0.5)
            break
        except httpx.HTTPError:
            time.sleep(0.05)
    else:
        raise RuntimeError("agent did not start in time")

    yield base_url
    server.should_exit = True
    thread.join(timeout=10)


@pytest.fixture()
def running_control_api(tmp_path, monkeypatch, running_agent, policies_file, fake_ollama_server):
    db_path = tmp_path / f"control-{uuid.uuid4().hex}.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("GPU_PROVIDER", "mock")
    monkeypatch.setenv("EXECUTION_AGENT_TOKEN", SHARED_AGENT_TOKEN)
    monkeypatch.setenv("EXECUTION_AGENT_URL", running_agent)
    monkeypatch.setenv("OLLAMA_LOCAL_URL", fake_ollama_server)
    monkeypatch.setenv("CLOUD_LLM_BASE_URL", "")
    monkeypatch.setenv("GPU_MONITOR_INTERVAL_SECONDS", "3600")
    get_settings.cache_clear()
    settings = get_settings()
    # Both the control API's FastAPI dependency (get_settings() returns
    # this same cached instance) and the worker (constructed directly with
    # this object below) must classify execution requests against the
    # SAME policies.yaml — the tmp one this fixture built to match
    # `workspace`, not the real repo config/policies.yaml.
    settings.config_dir = policies_file.parent
    engine = init_db(settings.database_url, create_all=True)

    with session_scope() as db:
        user = User(username="sam", password_hash=hash_password("correct-horse-battery-staple"))
        db.add(user)
        db.commit()

    from control.main import create_app

    port = _free_port()
    config = uvicorn.Config(create_app(), host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    base_url = f"http://127.0.0.1:{port}"
    deadline = time.time() + 10
    while time.time() < deadline:
        try:
            httpx.get(f"{base_url}/health", timeout=0.5)
            break
        except httpx.HTTPError:
            time.sleep(0.05)
    else:
        raise RuntimeError("control API did not start in time")

    yield base_url, settings

    server.should_exit = True
    thread.join(timeout=10)
    engine.dispose()


@pytest.fixture()
def api(running_control_api):
    base_url, _settings = running_control_api
    client = httpx.Client(base_url=base_url, timeout=30.0)
    resp = client.post("/api/auth/login", json={"username": "sam", "password": "correct-horse-battery-staple"})
    assert resp.status_code == 200, resp.text
    client.headers["Authorization"] = f"Bearer {resp.json()['access_token']}"
    yield client
    client.close()
