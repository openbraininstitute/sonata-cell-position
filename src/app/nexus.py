"""Nexus related functions."""

from itertools import chain
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Lock
from typing import TypeVar

import cachetools
import jwt
import requests
from entity_management.atlas import ParcellationOntology
from entity_management.base import Identifiable
from entity_management.core import Entity
from entity_management.simulation import DetailedCircuit
from requests import HTTPError
from starlette.status import (
    HTTP_200_OK,
    HTTP_401_UNAUTHORIZED,
    HTTP_403_FORBIDDEN,
    HTTP_500_INTERNAL_SERVER_ERROR,
)
from voxcell import RegionMap

from app.brain_region import load_alternative_region_map
from app.config import settings
from app.errors import ClientError
from app.logger import L
from app.schemas import NexusConfig
from app.utils import ensure_list

T = TypeVar("T", bound=Identifiable)

ENTITY_CACHE: cachetools.Cache = cachetools.TTLCache(
    maxsize=settings.ENTITY_CACHE_MAX_SIZE,
    ttl=settings.ENTITY_CACHE_TTL,
)
REGION_MAP_CACHE: cachetools.Cache = cachetools.TTLCache(
    maxsize=settings.REGION_MAP_CACHE_MAX_SIZE,
    ttl=settings.REGION_MAP_CACHE_TTL,
)
ALTERNATIVE_REGION_MAP_CACHE: cachetools.Cache = cachetools.TTLCache(
    maxsize=settings.ALTERNATIVE_REGION_MAP_CACHE_MAX_SIZE,
    ttl=settings.ALTERNATIVE_REGION_MAP_CACHE_TTL,
)


def _get_cached_resource_key(
    resource_class: type[T],
    resource_id: str | None,
    nexus_config: NexusConfig,
    cross_bucket=True,
) -> tuple:
    """Return the key to be used for the cache in load_cached_resource().

    The value of nexus_config.token is used to distinguish between
    authenticated and not authenticated requests.

    If nexus_config.token is set, it's assumed to be already validated by the proxy,
    so it's safe to use any cached data (even if retrieved with a different token).
    If it's not set, the resource is retrieved from Nexus without authentication, if possible.
    """
    # pylint: disable=unused-argument
    return (
        resource_class,
        resource_id,
        nexus_config.endpoint,
        nexus_config.bucket,
        bool(nexus_config.token),
    )


def _get_cached_region_map_key(
    resource: ParcellationOntology,
    nexus_config: NexusConfig,
) -> tuple:
    """Return the key to be used for the cache in load_cached_region_map().

    The value of nexus_config.token is used to distinguish between
    authenticated and not authenticated requests.

    If nexus_config.token is set, it's assumed to be already validated by the proxy,
    so it's safe to use any cached data (even if retrieved with a different token).
    If it's not set, the resource is retrieved from Nexus without authentication, if possible.
    """
    return (
        resource.get_id(),
        nexus_config.endpoint,
        nexus_config.bucket,
        bool(nexus_config.token),
    )


def _get_cached_alternative_region_map_key(
    resource: Entity,
    nexus_config: NexusConfig,
) -> tuple:
    """Return the key to be used for the cache in load_cached_alternative_region_map()."""
    return (
        resource.get_id(),
        nexus_config.endpoint,
        nexus_config.bucket,
        bool(nexus_config.token),
    )


@cachetools.cached(
    cache=ENTITY_CACHE,
    key=_get_cached_resource_key,
    lock=Lock(),
    info=settings.ENTITY_CACHE_INFO,
)
def load_cached_resource(
    resource_class: type[T],
    resource_id: str | None,
    nexus_config: NexusConfig,
    cross_bucket: bool = True,
) -> T:
    """Load and return an entity from Nexus.

    Args:
        resource_class: entity-management class of the resource to instantiate.
        resource_id: resource id.
        nexus_config: NexusConfig configuration.
        cross_bucket: True to search across all buckets, False otherwise.

    Returns:
        The resource instantiated from Nexus.
    """
    if not resource_id:
        raise ClientError("Resource id must be set")
    L.info("Loading {} with id {} from Nexus", resource_class.__name__, resource_id)
    try:
        resource = resource_class.from_id(
            resource_id,
            base=nexus_config.endpoint,
            org=nexus_config.org,
            proj=nexus_config.project,
            use_auth=nexus_config.token,
            cross_bucket=cross_bucket,
        )
    except HTTPError as ex:
        # return to the client any http error with Nexus to simplify the debugging
        raise ClientError(str(ex), status_code=ex.response.status_code) from ex
    if resource is None:
        raise ClientError(f"Resource not found: {resource_id}")
    return resource


@cachetools.cached(
    cache=REGION_MAP_CACHE,
    key=_get_cached_region_map_key,
    lock=Lock(),
    info=settings.REGION_MAP_CACHE_INFO,
)
def load_cached_region_map(resource: ParcellationOntology, nexus_config: NexusConfig) -> RegionMap:
    """Return the RegionMap instance for the given ParcellationOntology id.

    Warning: although the cache is thread safe, if this function is called from different threads,
    the function body may still be executed multiple times. Only the first result is cached.

    Args:
        resource: instance of ParcellationOntology.
        nexus_config: NexusConfig instance.

    Returns:
        The RegionMap instance loaded from json file.
    """
    L.info("Loading region map from Nexus")
    for data_download in resource.distribution:
        if data_download.encodingFormat == "application/json":
            with TemporaryDirectory() as tmp_dir:
                path = data_download.download(path=tmp_dir, use_auth=nexus_config.token)
                return RegionMap.load_json(path)
    raise ClientError(f"Hierarchy json not found for id {resource.get_id()}")


@cachetools.cached(
    cache=ALTERNATIVE_REGION_MAP_CACHE,
    key=_get_cached_alternative_region_map_key,
    lock=Lock(),
    info=settings.ALTERNATIVE_REGION_MAP_CACHE_INFO,
)
def load_cached_alternative_region_map(resource: Entity, nexus_config: NexusConfig) -> dict:
    """Return a dict extracted from the json-ld attached to the given Brain Region Ontology.

    Args:
        resource: instance of Entity representing the Brain Region Ontology.
        nexus_config: NexusConfig instance.

    Returns:
        The dict extracted from json-ld.
    """
    L.info("Loading alternative region map from Nexus")
    for data_download in ensure_list(resource.distribution):
        if data_download.encodingFormat == "application/ld+json":
            with TemporaryDirectory() as tmp_dir:
                path = data_download.download(path=tmp_dir, use_auth=nexus_config.token)
                result = load_alternative_region_map(path)
                L.info("Loaded {} alternative ids from {}", len(result), data_download.contentUrl)
                return result
    raise ClientError(f"Alternative hierarchy json not found for id {resource.get_id()}")


def get_circuit_config_path(resource: DetailedCircuit) -> Path:
    """Return the circuit config path contained in the given DetailedCircuit resource.

    Args:
        resource: instance of DetailedCircuit.

    Returns:
        The path to the circuit.
    """
    try:
        # retrieve and convert the url attribute to path
        path = resource.circuitConfigPath.get_url_as_path()
    except Exception as e:
        raise ClientError(f"Error in resource {resource.get_id()}: {e!r}") from e
    L.debug("Circuit config path: {}", path)
    return Path(path)


def _get_nexus_acl(nexus_config: NexusConfig) -> dict:
    """Call the /acls endpoint in Nexus and return the result.

    The payload returned by Nexus should be similar to:

    {
      "@context": [
        "https://bluebrain.github.io/nexus/contexts/metadata.json",
        "https://bluebrain.github.io/nexus/contexts/search.json",
        "https://bluebrain.github.io/nexus/contexts/acls.json"
      ],
      "_total": 1,
      "_results": [
        {
          "@id": "https://bbp.epfl.ch/nexus/v1/acls/bbp/mmb-point-neuron-framework-model",
          "@type": "AccessControlList",
          "acl": [
            {
              "identity": {
                "@id": "https://bbp.epfl.ch/nexus/v1/realms/bbp/groups/bbp-staff",
                "@type": "Group",
                "group": "/bbp-staff",
                "realm": "bbp"
              },
              "permissions": [
                "projects/read",
                "views/query",
                "gpfs-proj134/read",
                "resources/read",
                "gpfs-proj134/write",
                "resources/write",
                "files/write",
                "events/read"
              ]
            },
            {
              "identity": {
                "@id": "https://bbp.epfl.ch/nexus/v1/realms/bbp/groups/bbp-dev-proj134",
                "@type": "Group",
                "group": "/bbp-dev-proj134",
                "realm": "bbp"
              },
              "permissions": [
                "archives/write",
                "views/query",
                "gpfs-proj134/read",
                "resources/read",
                "views/write",
                "gpfs-proj134/write",
                "resources/write",
                "files/write",
                "events/read"
              ]
            }
          ],
          "_constrainedBy": "https://bluebrain.github.io/nexus/schemas/acls.json",
          "_createdAt": "2022-05-24T09:02:25.905Z",
          "_createdBy": "https://bbp.epfl.ch/nexus/v1/realms/serviceaccounts/users/username",
          "_deprecated": false,
          "_path": "/bbp/mmb-point-neuron-framework-model",
          "_rev": 13,
          "_self": "https://bbp.epfl.ch/nexus/v1/acls/bbp/mmb-point-neuron-framework-model",
          "_updatedAt": "2023-10-26T13:14:06.126Z",
          "_updatedBy": "https://bbp.epfl.ch/nexus/v1/realms/bbp/users/username"
        }
      ]
    }
    """
    response = requests.get(
        f"{nexus_config.endpoint}/acls/{nexus_config.bucket}",
        headers={"Authorization": f"Bearer {nexus_config.token}"},
        timeout=settings.NEXUS_AUTH_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


def is_user_authorized(nexus_config: NexusConfig) -> int:
    """Return the authorization status code for Nexus resources."""
    # pylint: disable=too-many-return-statements
    if not nexus_config.token:
        L.info("Missing authentication token")
        return HTTP_401_UNAUTHORIZED
    try:
        token_info = jwt.decode(nexus_config.token, options={"verify_signature": False})
    except jwt.exceptions.DecodeError as ex:
        L.info("Invalid authentication token: {}", ex)
        return HTTP_401_UNAUTHORIZED
    user = f"{token_info.get('preferred_username')} [{token_info.get('name')}]"
    permissions = settings.NEXUS_READ_PERMISSIONS.get(nexus_config.endpoint, {}).get(
        nexus_config.bucket
    )
    if not permissions:
        L.info(
            "User {} not authorized because of the Nexus endpoint and bucket: {}, {}",
            user,
            nexus_config.endpoint,
            nexus_config.bucket,
        )
        return HTTP_403_FORBIDDEN
    try:
        response = _get_nexus_acl(nexus_config)
    except requests.exceptions.HTTPError as ex:
        status_code = ex.response.status_code
        L.info("User {} not authorized because of the error from Nexus: {}", user, status_code)
        return status_code
    except requests.exceptions.RequestException as ex:
        L.info("User {} not authorized because of the error from Nexus: {}", user, ex)
        return HTTP_500_INTERNAL_SERVER_ERROR
    user_permissions = set(
        chain.from_iterable(
            acl["permissions"] for result in response["_results"] for acl in result["acl"]
        )
    )
    if missing := permissions - user_permissions:
        L.info("User {} not authorized because of permissions. Missing: {}", user, sorted(missing))
        return HTTP_403_FORBIDDEN
    L.info("User {} authorized", user)
    return HTTP_200_OK
