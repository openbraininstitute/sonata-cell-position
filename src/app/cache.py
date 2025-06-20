"""Circuit caching functions."""

import os
import shutil
import time
from pathlib import Path
from threading import Lock

import cachetools

import app.service
from app.config import settings
from app.libsonata_helper import convert_nodesets, sample_nodes, write_circuit_config
from app.logger import L
from app.schemas import CircuitCacheKey, CircuitCachePaths, CircuitParams, CircuitRef, UserContext
from app.utils import get_folder_size


class CircuitCache(cachetools.LRUCache):
    """Cache that can be used when an eviction callback is needed.

    Note: this class extends LRUCache and not TTLCache, because with TTLCache
    the method ``popitem()`` isn't called when an item expires.
    """

    def __init__(self, maxsize, getsizeof=None, eviction_callback=None):
        """Init the cache object."""
        super().__init__(maxsize=maxsize, getsizeof=getsizeof)
        self.eviction_callback = eviction_callback

    def popitem(self):
        """Evict a key and execute the eviction callback."""
        key, value = super().popitem()
        if self.eviction_callback:
            self.eviction_callback(key, value)
        return key, value


def _read_circuit_cache(paths: CircuitCachePaths) -> None:
    """Wait until the OK file is ready, in case it's being generated by a concurrent thread.

    Raise an exception in case of timeout or if the cache directory has been removed.
    """
    L.info("Reading cache: {}", paths.base)
    counter = settings.CIRCUIT_CACHE_CHECK_TIMEOUT // settings.CIRCUIT_CACHE_CHECK_INTERVAL
    while not paths.ok.exists() and counter > 0:
        time.sleep(settings.CIRCUIT_CACHE_CHECK_INTERVAL)
        counter -= 1
        if not paths.base.exists():
            # immediately exit in case the base directory has been removed,
            # for example because the concurrent thread failed to generate the files
            raise RuntimeError("The circuit cache has been removed while waiting to read it")
    if not paths.ok.exists():
        raise RuntimeError("Timeout while waiting to read the circuit cache")


def _write_circuit_cache(paths: CircuitCachePaths, key: CircuitCacheKey) -> None:
    """Write the circuit cache and the OK file."""
    L.info("Writing cache: {}", paths.base)
    try:
        sample_nodes(
            input_path=key.circuit_config_path,
            output_path=paths.nodes,
            population_name=key.population_name,
            sampling_ratio=key.sampling_ratio,
            seed=key.seed,
            attributes=key.attributes,
            id_mapping_path=paths.id_mapping,
        )
        convert_nodesets(
            input_path=key.circuit_config_path,
            output_path=paths.node_sets,
            id_mapping_path=paths.id_mapping,
        )
        write_circuit_config(
            circuit_config_path=paths.circuit_config,
            node_sets_path=paths.node_sets if paths.node_sets.is_file() else None,
            nodes_path=paths.nodes,
            node_populations=[key.population_name],
        )
        key.to_file(paths.metadata)
        paths.ok.touch(exist_ok=False)
    except BaseException:
        L.error("Failure to write the cache, removing any temporary file")
        shutil.rmtree(paths.base)
        raise


def _circuit_cache_getsizeof(value: CircuitCachePaths) -> int:
    """Return the size of the cached value."""
    size = get_folder_size(value.base)
    L.info("Size of {}: {} bytes", value.base, size)
    return size


def _circuit_cache_path() -> Path:
    """Return the base path to the circuit cache."""
    if path := os.getenv("CIRCUIT_CACHE_PATH"):
        return Path(path)
    tmpdir = os.getenv("TMPDIR", "/tmp")
    return Path(tmpdir).resolve() / "app_cache" / "circuits"


def _circuit_cache_eviction_callback(key: CircuitCacheKey, value: CircuitCachePaths) -> None:
    """Remove the base directory of the evicted item."""
    path = value.base.resolve()
    L.info("Key {} evicted, removing directory {}", key, path)
    assert path.is_relative_to(_circuit_cache_path())
    shutil.rmtree(path, ignore_errors=True)


# Cache of sampled circuits, having:
# - keys: instances of CircuitCacheKey.
# - values: instances of CircuitCachePaths having as `base` the directory containing the
#           sampled circuit. When an item is evicted, the directory is automatically deleted.
CIRCUIT_CACHE = CircuitCache(
    maxsize=settings.CIRCUIT_CACHE_MAX_SIZE_MB * 2**20,
    getsizeof=_circuit_cache_getsizeof,
    eviction_callback=_circuit_cache_eviction_callback,
)


@cachetools.cached(
    cache=CIRCUIT_CACHE,
    lock=Lock(),
    info=settings.CIRCUIT_CACHE_INFO,
)
def _get_sampled_circuit_paths(key: CircuitCacheKey) -> CircuitCachePaths:
    """Return the CircuitCachePaths corresponding to CircuitCacheKey.

    Warning: although the cache is thread safe, if this function is called from different threads,
    the function body may still be executed multiple times.

    Only the first thread will be able to create and populate the cache directory, while the others
    will wait until it's populated, or time out.
    """
    paths = CircuitCachePaths(base=_circuit_cache_path() / key.checksum())

    try:
        paths.base.mkdir(parents=True, exist_ok=False)
    except OSError:
        if not paths.base.is_dir():
            raise
        # the directory already exists because the circuit has already been sampled,
        # or it's being sampled in another process or thread, so wait until it's done
        _read_circuit_cache(paths)
    else:
        # the circuit needs to be sampled
        _write_circuit_cache(paths, key)

    return paths


def get_cached_circuit_params(
    user_context: UserContext,
    circuit_ref: CircuitRef,
    population_name: str,
    attributes: list[str],
    sampling_ratio: float,
    seed: int,
    use_circuit_cache: bool,
) -> CircuitParams:
    """Return an instance of CircuitParams, using the cache if possible."""
    path = app.service.get_circuit_config_path(circuit_ref, user_context=user_context)
    region_map = app.service.get_region_map(circuit_ref, user_context=user_context)
    alternative_region_map = app.service.get_alternative_region_map(
        circuit_ref, user_context=user_context
    )
    key = CircuitCacheKey(
        circuit_config_path=path,
        population_name=population_name,
        attributes=tuple(attributes),
        sampling_ratio=sampling_ratio,
        seed=seed,
    )
    if not use_circuit_cache or sampling_ratio > settings.CACHED_SAMPLING_RATIO:
        L.warning("Not caching nor using the sampled circuit")
    else:
        key = key.model_copy(
            update={
                "sampling_ratio": settings.CACHED_SAMPLING_RATIO,
            }
        )
        paths = _get_sampled_circuit_paths(key)
        # set circuit_config_path to the cached circuit config file,
        # and sampling_ratio to the newly calculated sampling ratio
        key = key.model_copy(
            update={
                "circuit_config_path": paths.circuit_config,
                "sampling_ratio": sampling_ratio / key.sampling_ratio,
            }
        )
    return CircuitParams(
        key=key,
        region_map=region_map,
        alternative_region_map=alternative_region_map,
    )
