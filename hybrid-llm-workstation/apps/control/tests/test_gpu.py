import time


def test_gpu_starts_off(client, auth_headers):
    resp = client.get("/api/gpu", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "OFF"


def test_gpu_full_lifecycle_with_mock_provider(client, auth_headers):
    resp = client.post("/api/gpu/start", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] in ("STARTING", "BOOTING", "READY")

    for _ in range(50):
        resp = client.get("/api/gpu", headers=auth_headers)
        if resp.json()["status"] == "READY":
            break
        time.sleep(0.1)
    body = resp.json()
    assert body["status"] == "READY", body
    assert body["endpoint"] is not None

    resp = client.get("/api/gpu/cost", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "READY"

    resp = client.post("/api/gpu/stop", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "OFF"


def test_starting_gpu_twice_is_idempotent(client, auth_headers):
    r1 = client.post("/api/gpu/start", headers=auth_headers)
    r2 = client.post("/api/gpu/start", headers=auth_headers)
    assert r1.status_code == 200
    assert r2.status_code == 200
    client.post("/api/gpu/stop", headers=auth_headers)


def test_stopping_off_gpu_is_a_noop(client, auth_headers):
    resp = client.post("/api/gpu/stop", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "OFF"


def test_gpu_status_requires_auth(client):
    resp = client.get("/api/gpu")
    assert resp.status_code == 401
