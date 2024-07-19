"""Common constants."""

import os

import numpy as np

ORIGINS = [
    "http://localhost:3000",
    "https://bbp.epfl.ch",
    "https://sonata.sbo.kcp.bbp.epfl.ch",
    "https://core-web-app-dev.sbo.kcp.bbp.epfl.ch",
    "https://bbpteam.epfl.ch",
    "https://openbluebrain.com",
    "https://openbluebrain.ch",
    "https://openbrainplatform.org",
    "https://openbrainplatform.com",
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

# Nexus endpoint and bucket can be specified by the user in the request headers.
# We may want to make them mandatory in the future, and remove the default values below.
NEXUS_ENDPOINT = "https://bbp.epfl.ch/nexus/v1"
NEXUS_BUCKET = "bbp/mmb-point-neuron-framework-model"

# to support other Nexus endpoints and buckets, the required permissions need to be added here. see
# https://bbpteam.epfl.ch/project/issues/browse/NSETM-2283?focusedId=234551#comment-234551
NEXUS_READ_PERMISSIONS = {
    "https://bbp.epfl.ch/nexus/v1": {
        "bbp/mmb-point-neuron-framework-model": {
            "events/read",
            "projects/read",
            "resources/read",
            "views/query",
            "gpfs-proj134/read",
        },
    },
    "https://staging.nise.bbp.epfl.ch/nexus/v1": {
        "bbp/mmb-point-neuron-framework-model": {
            "events/read",
            # "projects/read",  # not available in staging
            "resources/read",
            "views/query",
            # "gpfs-proj134/read",  # not available in staging
        },
    },
}
NEXUS_AUTH_TIMEOUT = 10  # in seconds

LOKY_EXECUTOR_ENABLED = bool(int(os.getenv("LOKY_EXECUTOR_ENABLED", "1")))
LOKY_EXECUTOR_MAX_WORKERS = 4  # maximum number of workers
LOKY_EXECUTOR_TIMEOUT = 2**31 // 1000  # seconds after which idle workers automatically shutdown
# any value greater than 2147483 (around 24.86 days) would cause OverflowError: timeout is too large
LOKY_START_METHOD = "loky"

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
