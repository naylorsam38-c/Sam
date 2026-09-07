def test_refresh_reports_local_unavailable_when_no_ollama(client, auth_headers):
    resp = client.post("/api/models/refresh", headers=auth_headers)
    assert resp.status_code == 200
    report = resp.json()
    assert report["local"]["healthy"] is False
    assert "could not reach Ollama" in report["local"]["detail"]
    assert report["cloud"]["detail"] == "CLOUD_LLM_BASE_URL not configured (GPU likely OFF)"


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
