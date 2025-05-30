"""Nexus related functions."""

from pathlib import Path

import jwt
import requests
from starlette.status import (
    HTTP_200_OK,
    HTTP_401_UNAUTHORIZED,
    HTTP_500_INTERNAL_SERVER_ERROR,
)

from app.config import settings
from app.constants import CIRCUITS
from app.errors import ClientError
from app.logger import L
from app.schemas import UserContext


def get_circuit_config_path(circuit_id) -> Path:
    """Return the circuit config path for the given circuit id.

    Args:
        circuit_id: circuit id.

    Returns:
        The path to the circuit.
    """
    try:
        path = CIRCUITS[circuit_id]
    except KeyError:
        msg = f"Circuit id not found: {circuit_id!r}"
        raise ClientError(msg) from None
    return Path(path)


def _get_keycloak_acl(credentials: str) -> dict:
    """Call the Keycloak endpoint and return the result."""
    auth_url = f"{settings.KEYCLOAK_URL}/protocol/openid-connect/userinfo"
    response = requests.get(
        auth_url,
        headers={"Authorization": f"Bearer {credentials}"},
        timeout=settings.KEYCLOAK_AUTH_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


def is_user_authorized(nexus_config: UserContext) -> int:
    """Return the authorization status code for Nexus resources."""
    # pylint: disable=too-many-return-statements
    if not nexus_config.token or not nexus_config.token.credentials:
        L.info("Missing auth token")
        return HTTP_401_UNAUTHORIZED
    try:
        token_info = jwt.decode(nexus_config.token.credentials, options={"verify_signature": False})
    except jwt.exceptions.DecodeError as ex:
        L.info("Invalid auth token: {}", ex)
        return HTTP_401_UNAUTHORIZED
    user = f"{token_info.get('preferred_username')} [{token_info.get('name')}]"
    try:
        _response = _get_keycloak_acl(nexus_config.token.credentials)
    except requests.exceptions.HTTPError as ex:
        status_code = ex.response.status_code
        L.info("User {} not authorized because of the error from Keycloak: {}", user, status_code)
        return status_code
    except requests.exceptions.RequestException as ex:
        L.info("User {} not authorized because of the error from Keycloak: {}", user, ex)
        return HTTP_500_INTERNAL_SERVER_ERROR
    # specific permissions could be checked here
    L.info("User {} authorized", user)
    return HTTP_200_OK
