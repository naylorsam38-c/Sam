"""Security-focused tests (spec section 22.3/22.4): authentication bypass
attempts, cross-user data access, and injection-style inputs. Complements
local-agent/tests/test_audit_and_bypass.py (the laptop-execution boundary)
and tests/unit/test_security.py (crypto primitives) with control-API-level
attack surface coverage.
"""

from __future__ import annotations

import jwt

from workstation_core.config import get_settings
from workstation_core.security import JWT_ALGORITHM


def test_none_algorithm_token_is_rejected(client, test_user):
    """The classic JWT 'alg=none' downgrade attack must not authenticate."""
    forged = jwt.encode({"sub": test_user.id, "username": test_user.username}, key="", algorithm="none")
    resp = client.get("/api/models", headers={"Authorization": f"Bearer {forged}"})
    assert resp.status_code == 401


def test_token_signed_with_wrong_secret_is_rejected(client, test_user):
    forged = jwt.encode({"sub": test_user.id, "username": test_user.username}, key="attacker-guess",
                        algorithm=JWT_ALGORITHM)
    resp = client.get("/api/models", headers={"Authorization": f"Bearer {forged}"})
    assert resp.status_code == 401


def test_expired_token_is_rejected(client, test_user):
    import datetime

    settings = get_settings()
    now = datetime.datetime.now(datetime.timezone.utc)
    expired = jwt.encode(
        {"sub": test_user.id, "username": test_user.username,
         "iat": now - datetime.timedelta(hours=2), "exp": now - datetime.timedelta(hours=1)},
        key=settings.auth_secret, algorithm=JWT_ALGORITHM,
    )
    resp = client.get("/api/models", headers={"Authorization": f"Bearer {expired}"})
    assert resp.status_code == 401


def test_token_for_deleted_user_is_rejected(client, db, test_user):
    from workstation_core.security import create_access_token

    token = create_access_token(test_user.id, test_user.username)
    db.delete(test_user)
    db.commit()
    resp = client.get("/api/models", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


def test_sql_injection_style_username_does_not_authenticate_or_error(client):
    resp = client.post("/api/auth/login", json={"username": "' OR '1'='1", "password": "' OR '1'='1"})
    assert resp.status_code == 401  # rejected cleanly, not a 500 (would indicate unsafe raw SQL)


def test_sql_injection_style_task_input_is_stored_inert_not_executed(client, auth_headers, db):
    from workstation_core.models_orm import ModelRecord

    model = ModelRecord(name="llama3.2:latest", environment="local", provider="ollama", engine="ollama",
                        status="available", capabilities=["chat"])
    db.add(model)
    db.commit()
    db.refresh(model)

    payload = {"messages": [{"role": "user", "content": "'; DROP TABLE tasks; --"}]}
    resp = client.post("/api/tasks", json={"type": "chat", "model_id": model.id, "input": payload},
                       headers=auth_headers)
    assert resp.status_code == 201

    # The tasks table must still exist and be queryable — nothing was executed.
    resp = client.get("/api/tasks", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["input"]["messages"][0]["content"] == "'; DROP TABLE tasks; --"


def test_missing_auth_header_on_every_mutating_endpoint(client):
    mutating = [
        ("POST", "/api/tasks", {"type": "chat"}),
        ("POST", "/api/gpu/start", None),
        ("POST", "/api/gpu/stop", None),
        ("POST", "/api/models/refresh", None),
        ("POST", "/api/execution/requests", {"operation": "read_file", "parameters": {}}),
    ]
    for method, path, body in mutating:
        resp = client.request(method, path, json=body)
        assert resp.status_code == 401, f"{method} {path} did not require auth"


def test_proxy_endpoint_cannot_be_used_to_reach_arbitrary_hosts(client, auth_headers):
    """The /proxy/cloud path parameter forwards to the live GPU endpoint
    only — it must not be usable as an open relay to arbitrary URLs even
    if a caller tries to smuggle one into the path or headers."""
    resp = client.get(
        "/proxy/cloud/../../etc/passwd",
        headers={"Authorization": "Bearer whatever-not-checked-here"},
    )
    # Either blocked by routing (404) or by the missing/invalid proxy
    # token (401) or "GPU not ready" (503) — never a 200 with arbitrary
    # host content, and never a 500.
    assert resp.status_code in (401, 404, 503)
