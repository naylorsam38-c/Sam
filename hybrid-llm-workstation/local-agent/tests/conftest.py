from __future__ import annotations

import time

import pytest
import yaml
from fastapi.testclient import TestClient

from agent.auth.signature import sign
from agent.config import AgentSettings
from agent.main import create_app

TOKEN = "test-shared-secret"


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
            {"operation": "list_directory", "level": "APPROVAL", "risk": "LOW", "allowed_paths": [str(workspace)]},
            {"operation": "write_file", "level": "APPROVAL", "risk": "MEDIUM", "allowed_paths": [str(workspace)]},
            {"operation": "run_command", "level": "APPROVAL", "risk": "MEDIUM", "allowed_paths": [str(workspace)],
             "allowed_commands": ["echo", "python3"]},
            {"operation": "run_tests", "level": "TRUSTED", "risk": "LOW", "allowed_paths": [str(workspace)],
             "allowed_commands": ["echo"]},
        ]
    }))
    return path


@pytest.fixture()
def settings(tmp_path, policies_file):
    return AgentSettings(
        execution_agent_token=TOKEN,
        policies_path=policies_file,
        audit_db_path=tmp_path / "audit.db",
        command_timeout_seconds=10,
        max_read_file_bytes=1_000_000,
    )


@pytest.fixture()
def client(settings):
    app = create_app(settings)
    with TestClient(app) as c:
        yield c


def signed_request(operation: str, parameters: dict, **extra) -> dict:
    request_id = extra.pop("request_id", "req-1")
    timestamp = extra.pop("timestamp", int(time.time()))
    signature = sign(request_id, operation, timestamp, TOKEN)
    body = {
        "request_id": request_id,
        "operation": operation,
        "parameters": parameters,
        "requested_by": "test-suite",
        "timestamp": timestamp,
        "signature": signature,
    }
    body.update(extra)
    return body
