import pytest

from control.deps import get_settings_dep
from tests.support.fake_agent import fake_agent_server


@pytest.fixture()
def agent(client):
    with fake_agent_server() as (url, received):
        overridden = client.app.state.settings.model_copy(update={"execution_agent_url": url})
        client.app.dependency_overrides[get_settings_dep] = lambda: overridden
        yield received
        client.app.dependency_overrides.pop(get_settings_dep, None)


def test_unknown_operation_is_denied_without_agent_contact(client, auth_headers, agent):
    resp = client.post(
        "/api/execution/requests",
        json={"operation": "delete_everything", "parameters": {}},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "DENIED"
    assert agent == []  # the agent was never even contacted


def test_path_outside_workspace_is_denied(client, auth_headers, agent):
    resp = client.post(
        "/api/execution/requests",
        json={"operation": "read_file", "parameters": {"path": "/etc/passwd"}},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["status"] == "DENIED"
    assert agent == []


def test_approval_flow_executes_after_approve(client, auth_headers, agent):
    resp = client.post(
        "/api/execution/requests",
        json={"operation": "read_file", "parameters": {"path": "~/workstation-workspace/notes.txt"}},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "AWAITING_APPROVAL"
    assert agent == []  # nothing runs until approved

    approvals = client.get("/api/approvals?status_=PENDING", headers=auth_headers).json()
    assert len(approvals) == 1
    approval_id = approvals[0]["id"]

    resp = client.post(f"/api/approvals/{approval_id}/approve", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "APPROVED"

    resp = client.get(f"/api/execution/requests/{body['id']}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "COMPLETED"
    assert len(agent) == 1
    assert agent[0]["operation"] == "read_file"
    assert "signature" in agent[0]


def test_deny_flow_never_contacts_agent(client, auth_headers, agent):
    resp = client.post(
        "/api/execution/requests",
        json={"operation": "write_file", "parameters": {"path": "~/workstation-workspace/out.txt"}},
        headers=auth_headers,
    )
    body = resp.json()
    approvals = client.get("/api/approvals?status_=PENDING", headers=auth_headers).json()
    approval_id = next(a["id"] for a in approvals if a["id"] == body["approval_id"])

    resp = client.post(f"/api/approvals/{approval_id}/deny", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "DENIED"

    resp = client.get(f"/api/execution/requests/{body['id']}", headers=auth_headers)
    assert resp.json()["status"] == "DENIED"
    assert agent == []


def test_execution_request_approve_shortcut_endpoint(client, auth_headers, agent):
    resp = client.post(
        "/api/execution/requests",
        json={"operation": "run_tests", "parameters": {"command": "pytest", "working_directory": "~/workstation-workspace"}},
        headers=auth_headers,
    )
    body = resp.json()
    resp = client.post(f"/api/execution/requests/{body['id']}/approve", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "COMPLETED"
    assert len(agent) == 1
