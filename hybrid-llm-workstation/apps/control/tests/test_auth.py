def test_login_success(client, test_user):
    resp = client.post("/api/auth/login", json={"username": "sam", "password": "correct-horse-battery-staple"})
    assert resp.status_code == 200
    assert resp.json()["token_type"] == "bearer"
    assert resp.json()["access_token"]


def test_login_wrong_password(client, test_user):
    resp = client.post("/api/auth/login", json={"username": "sam", "password": "wrong"})
    assert resp.status_code == 401


def test_login_unknown_user(client):
    resp = client.post("/api/auth/login", json={"username": "nobody", "password": "x"})
    assert resp.status_code == 401


def test_protected_endpoint_requires_token(client):
    resp = client.get("/api/models")
    assert resp.status_code == 401


def test_protected_endpoint_rejects_garbage_token(client):
    resp = client.get("/api/models", headers={"Authorization": "Bearer not-a-real-token"})
    assert resp.status_code == 401


def test_protected_endpoint_accepts_valid_token(client, auth_headers):
    resp = client.get("/api/models", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []
