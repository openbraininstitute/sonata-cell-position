"""Common constants."""
import os
from pathlib import Path

import numpy as np

ORIGINS = [
    "http://localhost:3000",
    "https://bbp.epfl.ch",
    "https://sonata.sbo.kcp.bbp.epfl.ch",
    "https://core-web-app-dev.sbo.kcp.bbp.epfl.ch",
    "https://bbpteam.epfl.ch",
]

PROJECT_PATH = os.environ.get("PROJECT_PATH")
COMMIT_SHA = os.environ.get("COMMIT_SHA")
DEBUG = os.environ.get("DEBUG", "").lower() == "true"
LOGGING_CONFIG = os.environ.get("LOGGING_CONFIG", "logging.yaml")
LOGGING_LEVEL = os.environ.get("LOGGING_LEVEL")
# maximum sampling ratio considered for caching
CACHED_SAMPLING_RATIO = float(os.getenv("CACHED_SAMPLING_RATIO", "0.01"))
# mapping from modality to attributes
MODALITIES = {
    "position": ["x", "y", "z"],
    "region": ["region"],
    "mtype": ["mtype"],
}
# enforced dtypes in the returned node DataFrame
DTYPES = {
    "x": np.float32,
    "y": np.float32,
    "z": np.float32,
    "region": "category",
    "mtype": "category",
    "layer": "category",
}
DYNAMICS_PREFIX = "@dynamics:"
MODALITIES_REGEX = f"^({'|'.join(MODALITIES)})$"

NEXUS_ENDPOINT = "https://bbp.epfl.ch/nexus/v1"
NEXUS_BUCKET = "bbp/mmb-point-neuron-framework-model"

ENTITY_CACHE_INFO = bool(int(os.getenv("ENTITY_CACHE_INFO", "0")))  # hits and misses
ENTITY_CACHE_MAX_SIZE = 100  # maximum number of entities to keep in memory
ENTITY_CACHE_TTL = 3600 * 24  # TTL in seconds

REGION_MAP_CACHE_INFO = bool(int(os.getenv("REGION_MAP_CACHE_INFO", "0")))  # hits and misses
REGION_MAP_CACHE_MAX_SIZE = 10  # maximum number of region maps to keep in memory
REGION_MAP_CACHE_TTL = 3600 * 24  # TTL in seconds

# circuit cache saved to disk (ideally RAM disk)
CIRCUIT_CACHE_INFO = bool(int(os.getenv("CIRCUIT_CACHE_INFO", "0")))  # hits and misses
CIRCUIT_CACHE_MAX_SIZE_MB = float(os.getenv("CIRCUIT_CACHE_MAX_SIZE_MB", "400"))
CIRCUIT_CACHE_CHECK_TIMEOUT = 600  # in seconds
CIRCUIT_CACHE_CHECK_INTERVAL = 1  # in seconds
CIRCUIT_CACHE_PATH = Path(os.getenv("TMPDIR", "/tmp"), "cache", "circuits").resolve()
