def test_refresh_reports_local_unavailable_when_no_ollama(client, auth_headers):
    resp = client.post("/api/models/refresh", headers=auth_headers)
    assert resp.status_code == 200
    report = resp.json()
    assert report["local"]["healthy"] is False
    assert "could not reach Ollama" in report["local"]["detail"]
    assert report["cloud"]["detail"] == "no cloud endpoint available (GPU is off, or CLOUD_LLM_BASE_URL is unset)"


def test_refresh_discovers_local_models_from_fake_ollama_server(client, auth_headers, fake_ollama_server):
    from control.deps import get_settings_dep

    overridden = client.app.state.settings.model_copy(update={"ollama_local_url": fake_ollama_server})
    client.app.dependency_overrides[get_settings_dep] = lambda: overridden

    resp = client.post("/api/models/refresh", headers=auth_headers)
    assert resp.status_code == 200
    report = resp.json()
    assert report["local"]["healthy"] is True
    assert report["local"]["models"] == 1

    resp = client.get("/api/models/local", headers=auth_headers)
    assert resp.status_code == 200
    models = resp.json()
    assert len(models) == 1
    assert models[0]["name"] == "llama3.2:latest"
    assert models[0]["status"] == "available"
    assert "chat" in models[0]["capabilities"]

    client.app.dependency_overrides.pop(get_settings_dep, None)


def test_refresh_discovers_cloud_models_via_live_gpu_endpoint_without_static_url(client, auth_headers):
    """CLOUD_LLM_BASE_URL is normally unset (a real provider hands out a
    new IP every session) — the registry must fall back to whatever the
    GPU lifecycle manager currently has on record as the live endpoint,
    not silently report the cloud as unconfigured forever."""
    import time

    client.post("/api/gpu/start", headers=auth_headers)
    for _ in range(50):
        if client.get("/api/gpu", headers=auth_headers).json()["status"] == "READY":
            break
        time.sleep(0.1)

    resp = client.post("/api/models/refresh", headers=auth_headers)
    assert resp.status_code == 200
    report = resp.json()
    assert report["cloud"]["healthy"] is True, report
    assert report["cloud"]["models"] == 1

    cloud_models = client.get("/api/models/cloud", headers=auth_headers).json()
    assert len(cloud_models) == 1
    assert cloud_models[0]["status"] == "available"

    client.post("/api/gpu/stop", headers=auth_headers)
