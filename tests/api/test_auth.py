import app.api.auth as test_module


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

    assert response.status_code == 401
    assert response.json() == {"message": "Unauthorized"}
