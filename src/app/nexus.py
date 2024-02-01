"""Nexus related functions."""

import logging
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Lock
from typing import TypeVar

import cachetools
from entity_management.atlas import ParcellationOntology
from entity_management.base import Identifiable
from entity_management.simulation import DetailedCircuit
from requests import HTTPError
from voxcell import RegionMap

from app.constants import (
    ENTITY_CACHE_INFO,
    ENTITY_CACHE_MAX_SIZE,
    ENTITY_CACHE_TTL,
    REGION_MAP_CACHE_INFO,
    REGION_MAP_CACHE_MAX_SIZE,
    REGION_MAP_CACHE_TTL,
)
from app.errors import ClientError
from app.schemas import NexusConfig

L = logging.getLogger(__name__)
T = TypeVar("T", bound=Identifiable)

ENTITY_CACHE: cachetools.Cache = cachetools.TTLCache(
    maxsize=ENTITY_CACHE_MAX_SIZE,
    ttl=ENTITY_CACHE_TTL,
)
REGION_MAP_CACHE: cachetools.Cache = cachetools.TTLCache(
    maxsize=REGION_MAP_CACHE_MAX_SIZE,
    ttl=REGION_MAP_CACHE_TTL,
)


@cachetools.cached(
    cache=ENTITY_CACHE,
    key=lambda resource_class, resource_id, *args, **kwargs: (resource_class, resource_id),
    lock=Lock(),
    info=ENTITY_CACHE_INFO,
)
def load_cached_resource(
    resource_class: type[T],
    resource_id: str | None,
    nexus_config: NexusConfig,
    cross_bucket=True,
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
    if not nexus_config.token:
        raise ClientError("Nexus token must be set")
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
        raise ClientError(str(ex)) from ex
    if resource is None:
        raise ClientError(f"Resource not found: {resource_id}")
    return resource


@cachetools.cached(
    cache=REGION_MAP_CACHE,
    key=lambda resource, *args, **kwargs: resource.get_id(),
    lock=Lock(),
    info=REGION_MAP_CACHE_INFO,
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
    for data_download in resource.distribution:
        if data_download.encodingFormat == "application/json":
            with TemporaryDirectory() as tmp_dir:
                path = data_download.download(path=tmp_dir, use_auth=nexus_config.token)
                return RegionMap.load_json(path)
    raise ClientError(f"Hierarchy json not found for id {resource.get_id()}")


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
    L.debug("Circuit config path: %s", path)
    return Path(path)
