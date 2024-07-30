"""Common constants."""

import numpy as np

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
