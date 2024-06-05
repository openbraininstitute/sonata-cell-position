import importlib.resources

import pytest
from voxcell import RegionMap

from app.constants import NEXUS_BUCKET, NEXUS_ENDPOINT
from app.schemas import CircuitRef, NexusConfig
from tests.utils import TEST_DATA_DIR

CIRCUIT_PATH = TEST_DATA_DIR / "circuit" / "circuit_config.json"


@pytest.fixture
def input_path():
    return CIRCUIT_PATH


@pytest.fixture
def circuit_ref_id():
    return CircuitRef(id="test-id")


@pytest.fixture
def circuit_ref_path(input_path):
    return CircuitRef(path=input_path)


@pytest.fixture
def nexus_config():
    return NexusConfig(
        endpoint=NEXUS_ENDPOINT,
        bucket=NEXUS_BUCKET,
    )


@pytest.fixture
def region_map():
    ref = importlib.resources.files("app") / "data" / "hierarchy.json"
    with importlib.resources.as_file(ref) as path:
        return RegionMap.load_json(path.absolute())
