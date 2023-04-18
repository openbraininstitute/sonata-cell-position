import libsonata
import pytest

import app.service as test_module
from tests.utils import TEST_DATA_DIR


@pytest.mark.parametrize(
    "input_path",
    [
        TEST_DATA_DIR / "circuit" / "circuit_config.json",
        TEST_DATA_DIR / "circuit" / "nodes.h5",
    ],
)
def test_get_node_population(input_path):
    result = test_module._get_node_population(input_path, population_name="default")
    assert isinstance(result, libsonata.NodePopulation)
    assert result.name == "default"


@pytest.mark.parametrize(
    "input_path",
    [
        TEST_DATA_DIR / "circuit" / "circuit_config.json",
        TEST_DATA_DIR / "circuit" / "nodes.h5",
    ],
)
def test_get_node_populations(input_path):
    result = test_module._get_node_populations(input_path)
    result = list(result)
    assert len(result) == 2
    for node_population, name in zip(result, ["default", "default2"]):
        assert isinstance(node_population, libsonata.NodePopulation)
        assert node_population.name == name
