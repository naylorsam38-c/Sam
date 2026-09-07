from conftest import signed_request


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_bad_signature_is_denied(client, workspace):
    body = signed_request("read_file", {"path": str(workspace)})
    body["signature"] = "0" * 64
    resp = client.post("/execute", json=body)
    assert resp.status_code == 200
    assert resp.json()["status"] == "DENIED"
    assert "signature" in resp.json()["stderr"]


def test_stale_timestamp_is_denied(client, workspace):
    body = signed_request("read_file", {"path": str(workspace)}, timestamp=1)
    resp = client.post("/execute", json=body)
    assert resp.json()["status"] == "DENIED"
    assert "timestamp" in resp.json()["stderr"]


def test_path_outside_workspace_is_denied_even_with_valid_signature(client, tmp_path):
    outside = tmp_path.parent / "definitely-not-the-workspace"
    body = signed_request("read_file", {"path": str(outside)})
    resp = client.post("/execute", json=body)
    assert resp.json()["status"] == "DENIED"
    assert "outside allowed_paths" in resp.json()["stderr"]


def test_approval_level_without_token_is_denied(client, workspace):
    (workspace / "notes.txt").write_text("hello")
    body = signed_request("read_file", {"path": str(workspace / "notes.txt")})
    resp = client.post("/execute", json=body)
    assert resp.json()["status"] == "DENIED"
    assert "approval" in resp.json()["stderr"].lower()


def test_approval_level_with_token_reads_the_file(client, workspace):
    (workspace / "notes.txt").write_text("hello from disk")
    body = signed_request("read_file", {"path": str(workspace / "notes.txt")}, approval_token="approval-123")
    resp = client.post("/execute", json=body)
    payload = resp.json()
    assert payload["status"] == "COMPLETED"
    assert payload["stdout"] == "hello from disk"


def test_write_then_read_round_trip(client, workspace):
    write_body = signed_request(
        "write_file", {"path": str(workspace / "out.txt"), "content": "written by agent"},
        approval_token="approval-1",
    )
    resp = client.post("/execute", json=write_body)
    assert resp.json()["status"] == "COMPLETED"
    assert (workspace / "out.txt").read_text() == "written by agent"

    read_body = signed_request("read_file", {"path": str(workspace / "out.txt")}, approval_token="approval-2")
    resp = client.post("/execute", json=read_body)
    assert resp.json()["stdout"] == "written by agent"


def test_list_directory(client, workspace):
    (workspace / "a.txt").write_text("a")
    (workspace / "sub").mkdir()
    body = signed_request("list_directory", {"path": str(workspace)}, approval_token="approval-1")
    resp = client.post("/execute", json=body)
    payload = resp.json()
    assert payload["status"] == "COMPLETED"
    names = [e["name"] for e in payload["result"]["entries"]]
    assert "a.txt" in names and "sub" in names


def test_run_command_with_disallowed_binary_is_denied(client, workspace):
    body = signed_request("run_command", {"command": "rm -rf /", "working_directory": str(workspace)},
                          approval_token="approval-1")
    resp = client.post("/execute", json=body)
    assert resp.json()["status"] == "DENIED"
    assert "allowed_commands" in resp.json()["stderr"]


def test_run_command_with_allowed_binary_executes(client, workspace):
    body = signed_request("run_command", {"command": "echo hello-agent", "working_directory": str(workspace)},
                          approval_token="approval-1")
    resp = client.post("/execute", json=body)
    payload = resp.json()
    assert payload["status"] == "COMPLETED"
    assert payload["exit_code"] == 0
    assert "hello-agent" in payload["stdout"]


def test_trusted_operation_runs_without_approval_token(client, workspace):
    body = signed_request("run_tests", {"command": "echo running-tests", "working_directory": str(workspace)})
    resp = client.post("/execute", json=body)
    payload = resp.json()
    assert payload["status"] == "COMPLETED"
    assert "running-tests" in payload["stdout"]


def test_unknown_operation_is_denied(client, workspace):
    body = signed_request("delete_everything", {"path": str(workspace)})
    resp = client.post("/execute", json=body)
    assert resp.json()["status"] == "DENIED"


def test_command_timeout_is_reported_as_failed(client, workspace, settings):
    settings.command_timeout_seconds = 1
    body = signed_request("run_command", {"command": "python3 -c \"import time; time.sleep(5)\"",
                                          "working_directory": str(workspace)}, approval_token="a")
    resp = client.post("/execute", json=body)
    payload = resp.json()
    assert payload["status"] == "FAILED"
    assert "timed out" in payload["stderr"]
