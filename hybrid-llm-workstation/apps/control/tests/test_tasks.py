from workstation_core.models_orm import ModelRecord


def _make_local_model(db, name="llama3.2:latest"):
    model = ModelRecord(name=name, environment="local", provider="ollama", engine="ollama",
                        status="available", capabilities=["chat"])
    db.add(model)
    db.commit()
    db.refresh(model)
    return model


def _make_cloud_model(db, name="large-qwen", status="unavailable"):
    model = ModelRecord(name=name, environment="cloud", provider="mock", engine="ollama",
                        status=status, capabilities=["chat"])
    db.add(model)
    db.commit()
    db.refresh(model)
    return model


def test_create_task_against_offline_cloud_model_succeeds(client, auth_headers, db):
    """A cloud model discovered on a previous session is 'unavailable' now
    because the GPU is off — selecting it is what should trigger a GPU
    start (via the worker), so task creation must not reject it."""
    model = _make_cloud_model(db)
    resp = client.post("/api/tasks", json={"type": "chat", "model_id": model.id, "input": {"messages": []}},
                       headers=auth_headers)
    assert resp.status_code == 201, resp.text
    assert resp.json()["environment"] == "cloud"


def test_create_task_against_offline_local_model_is_rejected(client, auth_headers, db):
    """Unlike cloud, a local model being unavailable means Ollama doesn't
    have it — nothing will make that spontaneously true."""
    model = _make_local_model(db)
    model.status = "unavailable"
    db.commit()
    resp = client.post("/api/tasks", json={"type": "chat", "model_id": model.id, "input": {"messages": []}},
                       headers=auth_headers)
    assert resp.status_code == 400


def test_create_task_requires_explicit_model_or_environment(client, auth_headers):
    resp = client.post("/api/tasks", json={"type": "chat", "input": {"messages": []}}, headers=auth_headers)
    assert resp.status_code == 400
    assert "Explicit choice is required" in resp.json()["detail"]


def test_create_task_rejects_unknown_model(client, auth_headers):
    resp = client.post("/api/tasks", json={"type": "chat", "model_id": "does-not-exist"}, headers=auth_headers)
    assert resp.status_code == 400


def test_create_and_fetch_task(client, auth_headers, db):
    model = _make_local_model(db)
    resp = client.post("/api/tasks", json={"type": "chat", "model_id": model.id, "input": {"messages": []}},
                       headers=auth_headers)
    assert resp.status_code == 201, resp.text
    task = resp.json()
    assert task["status"] == "QUEUED"
    assert task["model_id"] == model.id
    assert task["environment"] == "local"

    resp = client.get(f"/api/tasks/{task['id']}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == task["id"]


def test_cancel_task(client, auth_headers, db):
    model = _make_local_model(db)
    task = client.post("/api/tasks", json={"type": "chat", "model_id": model.id}, headers=auth_headers).json()
    resp = client.post(f"/api/tasks/{task['id']}/cancel", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "CANCELLED"

    # cancelling again is a no-op, not an error
    resp = client.post(f"/api/tasks/{task['id']}/cancel", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "CANCELLED"


def test_pause_then_resume_requeues_task(client, auth_headers, db):
    model = _make_local_model(db)
    task = client.post("/api/tasks", json={"type": "chat", "model_id": model.id}, headers=auth_headers).json()

    resp = client.post(f"/api/tasks/{task['id']}/pause", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "PAUSED"

    resp = client.post(f"/api/tasks/{task['id']}/resume", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "QUEUED"


def test_result_unavailable_before_completion(client, auth_headers, db):
    model = _make_local_model(db)
    task = client.post("/api/tasks", json={"type": "chat", "model_id": model.id}, headers=auth_headers).json()
    resp = client.get(f"/api/tasks/{task['id']}/result", headers=auth_headers)
    assert resp.status_code == 409


def test_task_not_visible_to_other_user(client, auth_headers, db):
    model = _make_local_model(db)
    task = client.post("/api/tasks", json={"type": "chat", "model_id": model.id}, headers=auth_headers).json()

    from workstation_core.security import create_access_token
    from workstation_core.models_orm import User
    other = User(username="mallory", password_hash="x")
    db.add(other)
    db.commit()
    db.refresh(other)
    other_token = create_access_token(other.id, other.username)

    resp = client.get(f"/api/tasks/{task['id']}", headers={"Authorization": f"Bearer {other_token}"})
    assert resp.status_code == 404
