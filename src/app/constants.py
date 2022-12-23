"""Common constants."""
import importlib.resources
import os

import numpy as np
import voxcell.region_map

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
ALLOWED_EXTENSIONS = {".json", ".h5"}
SAMPLING_RATIO = 0.01
CACHE_CHECK_TIMEOUT = 300
CACHE_CHECK_INTERVAL = 1
MODALITIES = {
    "position": ["x", "y", "z"],
    "region": ["region"],
    "mtype": ["mtype"],
}
DTYPES = {
    "x": np.float32,
    "y": np.float32,
    "z": np.float32,
    "region": "category",
    "mtype": "category",
}


with importlib.resources.path("app.data", "hierarchy.json") as path:
    REGION_MAP = voxcell.region_map.RegionMap.load_json(path.absolute())
