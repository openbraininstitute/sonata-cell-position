import logging
from unittest.mock import MagicMock

import jwt
import pytest
import requests

import app.auth as test_module


@pytest.fixture
def jwt_token():
    return jwt.encode(
        {
            "exp": 1706709167,
            "iat": 1706705567,
            "jti": "00000000-0000-0000-0000-000000000000",
            "iss": "https://example.com/auth/realms/BBP",
            "aud": "coreservices-kubernetes",
            "sub": "f:00000000-0000-0000-0000-000000000000:testuser",
            "typ": "Bearer",
            "azp": "bbp-workflow",
            "session_state": "00000000-0000-0000-0000-000000000000",
            "allowed-origins": ["*"],
            "realm_access": {"roles": ["offline_access"]},
            "scope": "profile offline_access openid groups email",
            "sid": "00000000-0000-0000-0000-000000000000",
            "email_verified": True,
            "name": "Test User",
            "preferred_username": "testuser",
            "given_name": "Test",
            "family_name": "User",
            "email": "test.user@example.org",
        },
        key="",
    )


def test_is_user_authorized_true(user_context, jwt_token, monkeypatch, caplog):
    caplog.set_level(logging.INFO)
    mock_response = MagicMock()
    mock_response.json.return_value = {}
    mock_get = MagicMock(return_value=mock_response)
    monkeypatch.setattr(test_module.requests, "get", mock_get)
    user_context.token.credentials = jwt_token

    result = test_module.is_user_authorized(user_context)

    assert result == 200
    assert "User testuser [Test User] authorized" in caplog.text
    assert mock_get.call_count == 1


def test_is_user_authorized_false_because_of_missing_token(user_context, caplog):
    caplog.set_level(logging.INFO)
    user_context.token = None

    result = test_module.is_user_authorized(user_context)

    assert result == 401
    assert "Missing auth token" in caplog.text


def test_is_user_authorized_false_because_of_invalid_token(user_context, caplog):
    caplog.set_level(logging.INFO)
    user_context.token.credentials = "invalid"

    result = test_module.is_user_authorized(user_context)

    assert result == 401
    assert "Invalid auth token" in caplog.text


def test_is_user_authorized_false_because_of_http_error(
    user_context, jwt_token, monkeypatch, caplog
):
    caplog.set_level(logging.INFO)
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
        response=MagicMock(status_code=403)
    )
    mock_get = MagicMock(return_value=mock_response)
    monkeypatch.setattr(test_module.requests, "get", mock_get)
    user_context.token.credentials = jwt_token

    result = test_module.is_user_authorized(user_context)

    assert result == 403
    assert (
        "User testuser [Test User] not authorized because of the error from Keycloak: 403"
        in caplog.text
    )
    assert mock_get.call_count == 1


def test_is_user_authorized_false_because_of_request_exception(
    user_context, jwt_token, monkeypatch, caplog
):
    caplog.set_level(logging.INFO)
    mock_get = MagicMock(side_effect=requests.exceptions.SSLError("SSL Error"))
    monkeypatch.setattr(test_module.requests, "get", mock_get)
    user_context.token.credentials = jwt_token

    result = test_module.is_user_authorized(user_context)

    assert result == 500
    assert (
        "User testuser [Test User] not authorized because of the error from Keycloak: SSL Error"
        in caplog.text
    )
    assert mock_get.call_count == 1
