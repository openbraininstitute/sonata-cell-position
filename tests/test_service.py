from unittest.mock import MagicMock, patch

import pytest
import voxcell

import app.service as test_module
from app.errors import CircuitError
from tests.utils import assert_cache, clear_cache


@patch(f"{test_module.__name__}.nexus.load_cached_resource")
def test_get_circuit_config_path_from_id(
    mock_load_cached_resource, nexus_config, circuit_ref_id, input_path
):
    resource = MagicMock()
    resource.circuitConfigPath.get_url_as_path.return_value = str(input_path)
    mock_load_cached_resource.return_value = resource
    nexus_config.token = "test-token"

    result = test_module.get_circuit_config_path(circuit_ref_id, nexus_config=nexus_config)

    assert result == input_path
    assert mock_load_cached_resource.call_count == 1


def test_get_circuit_config_path_from_path(nexus_config, circuit_ref_path):
    result = test_module.get_circuit_config_path(circuit_ref_path, nexus_config=nexus_config)

    assert result == circuit_ref_path.path


def test_get_single_node_population_name_raises(circuit_ref_path, nexus_config):
    with pytest.raises(
        CircuitError, match="population_name must be specified when there are multiple populations"
    ):
        test_module.get_single_node_population_name(circuit_ref_path, nexus_config=nexus_config)


def test_get_bundled_region_map():
    with clear_cache(test_module.get_bundled_region_map) as tested_func:
        result = test_module.get_bundled_region_map()

        assert_cache(tested_func, hits=0, misses=1, currsize=1)
        assert isinstance(result, voxcell.RegionMap)
        assert result.get(997, "acronym") == "root"


def test_get_region_map_from_circuit_path(nexus_config, circuit_ref_path):
    result = test_module.get_region_map(circuit_ref_path, nexus_config=nexus_config)

    assert isinstance(result, voxcell.RegionMap)
    assert result.get(997, "acronym") == "root"


@patch(f"{test_module.__name__}.nexus.load_cached_region_map")
@patch(f"{test_module.__name__}.nexus.load_cached_resource")
def test_get_region_map_from_circuit_id(
    mock_load_cached_resource, mock_load_cached_region_map, nexus_config, circuit_ref_id, region_map
):
    mock_load_cached_region_map.return_value = region_map
    result = test_module.get_region_map(circuit_ref_id, nexus_config=nexus_config)

    assert isinstance(result, voxcell.RegionMap)
    assert result.get(997, "acronym") == "root"
    assert mock_load_cached_region_map.call_count == 1
    assert mock_load_cached_resource.call_count == 3


@pytest.mark.parametrize(
    "regions, expected",
    [
        ([], []),
        (["838"], ["SSp-n2/3", "SSp-n2", "SSp-n3"]),
        (["SSp-n2/3"], ["SSp-n2/3", "SSp-n2", "SSp-n3"]),
        (["838", "SSp-n2/3"], ["SSp-n2/3", "SSp-n2", "SSp-n3"]),
    ],
)
def test_region_acronyms(regions, expected, region_map):
    result = test_module._region_acronyms(regions, region_map=region_map)

    assert set(result) == set(expected)
    assert len(result) == len(expected)


@pytest.mark.parametrize(
    "regions",
    [
        ["9999999999999999"],
        ["838", "9999999999999999"],
        ["unknown_region_acronym"],
        ["838", "unknown_region_acronym"],
    ],
)
def test_region_acronyms_not_found(regions, region_map):
    with pytest.raises(CircuitError, match="No region ids found with region"):
        test_module._region_acronyms(regions, region_map=region_map)
