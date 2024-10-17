import app.api.root as test_module


async def test_root_get(api_client):
    response = await api_client.get("/", follow_redirects=False)

    assert response.status_code == 302
    assert response.next_request.url.path == "/docs"


async def test_health_get(api_client):
    response = await api_client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "OK"}
    assert response.headers["Cache-Control"] == "no-cache"


async def test_version_get(api_client, monkeypatch):
    app_name = "sonata-cell-position"
    app_version = "2000.0.0"
    commit_sha = "12345678"
    monkeypatch.setattr(test_module.settings, "APP_NAME", app_name)
    monkeypatch.setattr(test_module.settings, "APP_VERSION", app_version)
    monkeypatch.setattr(test_module.settings, "COMMIT_SHA", commit_sha)

    response = await api_client.get("/version")

    assert response.status_code == 200
    assert response.json() == {
        "app_name": app_name,
        "app_version": app_version,
        "commit_sha": commit_sha,
    }
    assert response.headers["Cache-Control"] == "no-cache"
