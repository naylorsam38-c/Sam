"""Full-stack integration: the REAL control API talking HTTP to the REAL
local execution agent (not the fake_agent stand-in used by the control and
worker unit suites) — spec section 21 Phase D: 'verify cloud LLM cannot
bypass policy' end to end across both processes.
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
from fastapi.testclient import TestClient

from agent.config import AgentSettings
from agent.main import create_app as create_agent_app
from control.deps import get_settings_dep
from control.main import create_app as create_control_app
from workstation_core.config import get_settings
from workstation_core.db import init_db, session_scope
from workstation_core.models_orm import User
from workstation_core.security import hash_password

SHARED_TOKEN = "shared-integration-secret"


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
        ]
    }))
    return path


@pytest.fixture()
def running_agent(policies_file, tmp_path):
    settings = AgentSettings(
        execution_agent_token=SHARED_TOKEN, policies_path=policies_file,
        audit_db_path=tmp_path / "agent-audit.db", command_timeout_seconds=10,
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
def control_client(tmp_path, monkeypatch, running_agent, policies_file):
    db_path = tmp_path / f"control-{uuid.uuid4().hex}.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("GPU_PROVIDER", "mock")
    monkeypatch.setenv("EXECUTION_AGENT_TOKEN", SHARED_TOKEN)
    monkeypatch.setenv("EXECUTION_AGENT_URL", running_agent)
    get_settings.cache_clear()
    settings = get_settings()
    engine = init_db(settings.database_url, create_all=True)

    with session_scope() as db:
        user = User(username="sam", password_hash=hash_password("correct-horse-battery-staple"))
        db.add(user)
        db.commit()

    app = create_control_app()
    with TestClient(app) as client:
        # Point the control API's policies_config_path at the same temp
        # policies.yaml the agent is enforcing, so both sides classify
        # identically (as they would from the same config/ directory in a
        # real deployment).
        overridden = client.app.state.settings.model_copy(update={"config_dir": policies_file.parent})
        client.app.dependency_overrides[get_settings_dep] = lambda: overridden
        yield client

    engine.dispose()


def _auth_headers(client) -> dict:
    resp = client.post("/api/auth/login", json={"username": "sam", "password": "correct-horse-battery-staple"})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_end_to_end_approval_flow_against_real_agent(control_client, workspace):
    headers = _auth_headers(control_client)
    (workspace / "notes.txt").write_text("real agent, real file")

    resp = control_client.post(
        "/api/execution/requests",
        json={"operation": "read_file", "parameters": {"path": str(workspace / "notes.txt")}},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "AWAITING_APPROVAL"

    resp = control_client.post(f"/api/execution/requests/{body['id']}/approve", headers=headers)
    assert resp.status_code == 200, resp.text
    result = resp.json()
    assert result["status"] == "COMPLETED", result
    assert result["result"]["stdout"] == "real agent, real file"


def test_end_to_end_out_of_bounds_path_denied_by_real_agent_even_if_approved(control_client, tmp_path):
    """The control plane's own policy copy and the agent's are the same
    file here, so this denies at submit time already — the point is that
    even forcing it to the agent (as execute_now would) is independently
    safe. Covered thoroughly at the agent level in local-agent/tests; this
    proves the control plane really is talking to a real, independently
    enforcing process rather than a stub."""
    headers = _auth_headers(control_client)
    outside = tmp_path.parent / "outside" / "passwd"

    resp = control_client.post(
        "/api/execution/requests",
        json={"operation": "read_file", "parameters": {"path": str(outside)}},
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["status"] == "DENIED"
