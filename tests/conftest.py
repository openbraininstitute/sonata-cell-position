import pytest

from tests.utils import TEST_DATA_DIR

CIRCUIT_PATH = TEST_DATA_DIR / "circuit" / "circuit_config.json"
NODES_PATH = TEST_DATA_DIR / "circuit" / "nodes.h5"


@pytest.fixture(
    params=[
        CIRCUIT_PATH,
        NODES_PATH,
    ],
)
def input_path(request):
    yield request.param


@pytest.fixture
def nodes_path():
    return NODES_PATH


@pytest.fixture
def circuit_path():
    return CIRCUIT_PATH
