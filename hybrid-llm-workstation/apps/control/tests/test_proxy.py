import time

from control.deps import get_settings_dep

PROXY_TOKEN = "webui-proxy-secret"


def _with_proxy_token(client):
    overridden = client.app.state.settings.model_copy(update={"open_webui_proxy_token": PROXY_TOKEN})
    client.app.dependency_overrides[get_settings_dep] = lambda: overridden
    return overridden


def test_proxy_requires_token(client, auth_headers):
    resp = client.get("/proxy/cloud/api/tags")
    assert resp.status_code in (401, 503)


def test_proxy_rejects_wrong_token(client, auth_headers):
    _with_proxy_token(client)
    resp = client.get("/proxy/cloud/api/tags", headers={"Authorization": "Bearer wrong-token"})
    assert resp.status_code == 401
    client.app.dependency_overrides.pop(get_settings_dep, None)


def test_proxy_503_when_gpu_off(client, auth_headers):
    _with_proxy_token(client)
    resp = client.get("/proxy/cloud/api/tags", headers={"Authorization": f"Bearer {PROXY_TOKEN}"})
    assert resp.status_code == 503
    client.app.dependency_overrides.pop(get_settings_dep, None)


def test_proxy_forwards_to_ready_cloud_gpu(client, auth_headers):
    _with_proxy_token(client)

    client.post("/api/gpu/start", headers=auth_headers)
    for _ in range(50):
        if client.get("/api/gpu", headers=auth_headers).json()["status"] == "READY":
            break
        time.sleep(0.1)

    resp = client.get("/proxy/cloud/api/tags", headers={"Authorization": f"Bearer {PROXY_TOKEN}"})
    assert resp.status_code == 200
    assert "models" in resp.json()

    resp = client.post(
        "/proxy/cloud/api/chat",
        json={"model": "mock-cloud-model", "messages": [{"role": "user", "content": "hi"}]},
        headers={"Authorization": f"Bearer {PROXY_TOKEN}"},
    )
    assert resp.status_code == 200
    assert "mock cloud GPU response" in resp.json()["message"]["content"]

    # the proxy'd chat call should have marked the GPU busy-then-released
    gpu_status = client.get("/api/gpu", headers=auth_headers).json()
    assert gpu_status["status"] in ("READY", "IDLE")

    client.post("/api/gpu/stop", headers=auth_headers)
    client.app.dependency_overrides.pop(get_settings_dep, None)
