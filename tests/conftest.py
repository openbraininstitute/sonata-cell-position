import pytest

from tests.utils import TEST_DATA_DIR


@pytest.fixture(
    params=[
        TEST_DATA_DIR / "circuit" / "circuit_config.json",
        TEST_DATA_DIR / "circuit" / "nodes.h5",
    ],
)
def input_path(request):
    yield request.param
