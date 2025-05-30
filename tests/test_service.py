import pytest
import voxcell

import app.service as test_module
from app.constants import CIRCUITS
from app.errors import CircuitError

from tests.utils import assert_cache, clear_cache


def test_get_circuit_config_path_from_id(
    nexus_config, circuit_ref_id, circuit_id, input_path, monkeypatch
):
    monkeypatch.setitem(CIRCUITS, circuit_id, input_path)

    result = test_module.get_circuit_config_path(circuit_ref_id, nexus_config=nexus_config)

    assert result == input_path


def test_get_circuit_config_path_from_path(nexus_config, circuit_ref_path):
    result = test_module.get_circuit_config_path(circuit_ref_path, nexus_config=nexus_config)

    assert result == circuit_ref_path.path


def test_get_single_node_population_name_raises(circuit_ref_path, nexus_config):
    with pytest.raises(
        CircuitError, match="Exactly one node population must be present in the circuit"
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


def test_get_region_map_from_circuit_id(nexus_config, circuit_ref_id):
    result = test_module.get_region_map(circuit_ref_id, nexus_config=nexus_config)

    assert isinstance(result, voxcell.RegionMap)
    assert result.get(997, "acronym") == "root"


def test_get_alternative_region_map(nexus_config, circuit_ref_id):
    result = test_module.get_alternative_region_map(circuit_ref_id, nexus_config=nexus_config)

    assert isinstance(result, dict)
    region_id = "http://bbp.epfl.ch/neurosciencegraph/ontologies/core/brainregion/Isocortex_L4"
    expected_ids = [
        148,
        759,
        913,
        234,
        480149298,
        12995,
        635,
        545,
        990,
        1010,
        816,
        678,
        480149270,
        480149326,
    ]
    assert sorted(result[region_id]) == sorted(expected_ids)


@pytest.mark.parametrize(
    "regions, expected",
    [
        ([], []),
        (["838"], ["SSp-n2/3", "SSp-n2", "SSp-n3"]),
        (["SSp-n2/3"], ["SSp-n2/3", "SSp-n2", "SSp-n3"]),
        (["838", "SSp-n2/3"], ["SSp-n2/3", "SSp-n2", "SSp-n3"]),
        (
            ["http://bbp.epfl.ch/neurosciencegraph/ontologies/core/brainregion/RSP_L4"],
            [
                "RSPd4",
                "VISm4",
                "VISmma4",
                "VISmmp4",
            ],
        ),
    ],
)
def test_region_acronyms(regions, expected, region_map, alternative_region_map):
    result = test_module._region_acronyms(
        regions, region_map=region_map, alternative_region_map=alternative_region_map
    )

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
def test_region_acronyms_not_found(regions, region_map, alternative_region_map):
    with pytest.raises(CircuitError, match="No region ids found with region"):
        test_module._region_acronyms(
            regions, region_map=region_map, alternative_region_map=alternative_region_map
        )
