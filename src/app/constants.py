"""Common constants."""
import os

import numpy as np

ORIGINS = [
    "http://localhost:3000",
    "https://bbp.epfl.ch",
    "https://sonata.sbo.kcp.bbp.epfl.ch",
]

PROJECT_PATH = os.environ.get("PROJECT_PATH")
COMMIT_SHA = os.environ.get("COMMIT_SHA")
DEBUG = os.environ.get("DEBUG", "").lower() == "true"
LOGGING_CONFIG = os.environ.get("LOGGING_CONFIG", "logging.yaml")
LOGGING_LEVEL = os.environ.get("LOGGING_LEVEL")
ALLOWED_EXTENSIONS = {".json", ".h5"}
SAMPLING_RATIO = 0.01
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
