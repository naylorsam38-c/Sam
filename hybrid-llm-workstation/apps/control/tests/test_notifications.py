def test_notification_created_on_gpu_start_and_stop(client, auth_headers):
    import time

    client.post("/api/gpu/start", headers=auth_headers)
    for _ in range(50):
        if client.get("/api/gpu", headers=auth_headers).json()["status"] == "READY":
            break
        time.sleep(0.1)
    client.post("/api/gpu/stop", headers=auth_headers)

    resp = client.get("/api/notifications", headers=auth_headers)
    assert resp.status_code == 200
    types = [n["type"] for n in resp.json()]
    assert "gpu_started" in types
    assert "gpu_stopped" in types


def test_mark_notification_read(client, auth_headers):
    import time

    client.post("/api/gpu/start", headers=auth_headers)
    for _ in range(50):
        if client.get("/api/gpu", headers=auth_headers).json()["status"] == "READY":
            break
        time.sleep(0.1)

    notifications = client.get("/api/notifications?unread_only=true", headers=auth_headers).json()
    assert len(notifications) >= 1
    nid = notifications[0]["id"]

    resp = client.post(f"/api/notifications/{nid}/read", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "read"

    resp = client.get("/api/notifications?unread_only=true", headers=auth_headers)
    assert nid not in [n["id"] for n in resp.json()]
    client.post("/api/gpu/stop", headers=auth_headers)


def test_cannot_read_other_users_notification(client, auth_headers, db):
    from workstation_core.models_orm import Notification, User
    from workstation_core.security import create_access_token

    other = User(username="eve", password_hash="x")
    db.add(other)
    db.commit()
    db.refresh(other)

    note = Notification(user_id=other.id, type="task_completed", title="not yours", body="")
    db.add(note)
    db.commit()
    db.refresh(note)

    resp = client.post(f"/api/notifications/{note.id}/read", headers=auth_headers)
    assert resp.status_code == 404
