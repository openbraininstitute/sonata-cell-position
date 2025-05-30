"""Authorization functions."""

import jwt
import requests
from starlette.status import HTTP_200_OK, HTTP_401_UNAUTHORIZED, HTTP_500_INTERNAL_SERVER_ERROR

from app.config import settings
from app.logger import L
from app.schemas import UserContext


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


def is_user_authorized(user_context: UserContext) -> int:
    """Return the authorization status code."""
    # pylint: disable=too-many-return-statements
    if not user_context.token or not user_context.token.credentials:
        L.info("Missing auth token")
        return HTTP_401_UNAUTHORIZED
    try:
        token_info = jwt.decode(user_context.token.credentials, options={"verify_signature": False})
    except jwt.exceptions.DecodeError as ex:
        L.info("Invalid auth token: {}", ex)
        return HTTP_401_UNAUTHORIZED
    user = f"{token_info.get('preferred_username')} [{token_info.get('name')}]"
    try:
        _response = _get_keycloak_acl(user_context.token.credentials)
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
