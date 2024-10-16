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


async def test_auth_get_success(api_client_with_auth, monkeypatch):
    monkeypatch.setattr(test_module.nexus, "is_user_authorized", lambda _: 200)

    response = await api_client_with_auth.get("/auth")

    assert response.status_code == 200
    assert response.json() == {"message": "OK"}


async def test_auth_get_failure_with_headers(api_client_with_auth):
    response = await api_client_with_auth.get("/auth")

    assert response.status_code == 401
    assert response.json() == {"message": "Unauthorized"}


async def test_auth_get_failure_without_headers(api_client):
    response = await api_client.get("/auth")

    assert response.status_code == 422
    assert response.json() == {
        "detail": [
            {
                "type": "missing",
                "loc": ["header", "nexus-endpoint"],
                "msg": "Field required",
                "input": None,
            },
            {
                "type": "missing",
                "loc": ["header", "nexus-bucket"],
                "msg": "Field required",
                "input": None,
            },
            {
                "type": "missing",
                "loc": ["header", "nexus-token"],
                "msg": "Field required",
                "input": None,
            },
        ]
    }
