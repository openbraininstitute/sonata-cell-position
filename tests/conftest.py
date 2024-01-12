import pytest

from tests.utils import TEST_DATA_DIR

CIRCUIT_PATH = TEST_DATA_DIR / "circuit" / "circuit_config.json"


@pytest.fixture
def input_path():
    return CIRCUIT_PATH
