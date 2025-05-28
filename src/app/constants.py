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

CIRCUITS = {
    "https://bbp.epfl.ch/data/bbp/mmb-point-neuron-framework-model/2b29d249-6520-4a98-9586-27ec7803aed2": "/gpfs/bbp.cscs.ch/data/scratch/proj134/workflow-outputs/05072024-atlas-release-v1.0.1-full/cellPositionConfig/root/build/circuit_config.json",  # noqa: E501
}
