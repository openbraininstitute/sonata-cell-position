import libsonata
import pytest

import app.libsonata_helper as test_module


def test_get_node_population(input_path):
    result = test_module.get_node_population(input_path, population_name="default")
    assert isinstance(result, libsonata.NodePopulation)
    assert result.name == "default"


def test_get_node_population_raises(input_path):
    with pytest.raises(
        ValueError, match="population_name must be specified when there are multiple populations"
    ):
        test_module.get_node_population(input_path)


def test_get_node_populations(input_path):
    result = test_module.get_node_populations(input_path)
    result = list(result)
    assert len(result) == 2
    for node_population, name in zip(result, ["default", "default2"]):
        assert isinstance(node_population, libsonata.NodePopulation)
        assert node_population.name == name
