import re

import libsonata
import pytest

from tests.utils import TEST_DATA_DIR, _assert_populations_equal, _get_node_population, edit_json


@pytest.mark.usefixtures(
    "_patch_get_circuit_config_path", "_patch_get_region_map", "_patch_get_alternative_region_map"
)
async def test_read_circuit(api_client_with_auth, circuit_id):
    response = await api_client_with_auth.get(
        "/circuit",
        params={
            "circuit_id": circuit_id,
            "population_name": "default",
            "how": "json",
            "modality": ["position", "mtype"],
            "sampling_ratio": 0.5,
            "seed": 102,
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "mtype": {"0": "L6_Y"},
        "x": {"0": 201.0},
        "y": {"0": 202.0},
        "z": {"0": 203.0},
    }


@pytest.mark.usefixtures(
    "_patch_get_circuit_config_path", "_patch_get_region_map", "_patch_get_alternative_region_map"
)
async def test_read_circuit_unknown_region_id(api_client_with_auth, circuit_id):
    response = await api_client_with_auth.get(
        "/circuit",
        params={
            "circuit_id": circuit_id,
            "population_name": "default",
            "how": "json",
            "modality": ["position", "mtype"],
            "region": 9999999999999999,
            "sampling_ratio": 0.5,
            "seed": 102,
        },
    )

    assert response.status_code == 400
    assert response.json() == {
        "message": "CircuitError: No region ids found with region '9999999999999999'"
    }


@pytest.mark.usefixtures(
    "_patch_get_circuit_config_path", "_patch_get_region_map", "_patch_get_alternative_region_map"
)
async def test_read_circuit_unknown_region_label(api_client_with_auth, circuit_id):
    response = await api_client_with_auth.get(
        "/circuit",
        params={
            "circuit_id": circuit_id,
            "population_name": "default",
            "how": "json",
            "modality": ["position", "mtype"],
            "region": "unknown_region_acronym",
            "sampling_ratio": 0.5,
            "seed": 102,
        },
    )

    assert response.status_code == 400
    assert response.json() == {
        "message": "CircuitError: No region ids found with region 'unknown_region_acronym'"
    }


async def test_read_circuit_invalid_modality(api_client_with_auth, circuit_id):
    response = await api_client_with_auth.get(
        "/circuit",
        params={
            "circuit_id": circuit_id,
            "population_name": "default",
            "how": "json",
            "modality": ["position", "invalid"],
            "sampling_ratio": 0.5,
            "seed": 102,
        },
    )

    assert response.status_code == 422
    response_json = response.json()
    assert len(response_json["detail"]) == 1
    error = response_json["detail"][0]
    assert error["type"] == "string_pattern_mismatch"
    assert error["loc"] == ["query", "modality", 1]
    assert error["msg"].startswith("String should match pattern")
    assert error["input"] == "invalid"


@pytest.mark.usefixtures(
    "_patch_get_circuit_config_path", "_patch_get_region_map", "_patch_get_alternative_region_map"
)
async def test_query(api_client_with_auth, circuit_id):
    response = await api_client_with_auth.post(
        "/circuit/query",
        json={
            "circuit_id": circuit_id,
            "population_name": "default",
            "how": "json",
            "attributes": ["x", "y", "z", "mtype"],
            "sampling_ratio": 0.5,
            "seed": 102,
            "queries": [{"mtype": "L6_Y"}],
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "mtype": {"0": "L6_Y"},
        "x": {"0": 201.0},
        "y": {"0": 202.0},
        "z": {"0": 203.0},
    }


async def test_query_invalid_key(api_client_with_auth, circuit_id):
    response = await api_client_with_auth.post(
        "/circuit/query",
        json={
            "circuit_id": circuit_id,
            "population_name": "default",
            "how": "json",
            "attributes": ["x", "y", "z", "mtype"],
            "sampling_ratio": 0.5,
            "seed": 102,
            "queries": [{"mtype": "L6_Y"}],
            "invalid": "value",
        },
    )

    assert response.status_code == 422
    response_json = response.json()
    assert len(response_json["detail"]) == 1
    error = response_json["detail"][0]
    assert error["type"] == "extra_forbidden"
    assert error["loc"] == ["body", "invalid"]
    assert error["msg"] == "Extra inputs are not permitted"
    assert error["input"] == "value"


async def test_query_invalid_how(api_client_with_auth, circuit_id):
    response = await api_client_with_auth.post(
        "/circuit/query",
        json={
            "circuit_id": circuit_id,
            "population_name": "default",
            "how": "invalid",
            "attributes": ["x", "y", "z", "mtype"],
            "sampling_ratio": 0.5,
            "seed": 102,
            "queries": [{"mtype": "L6_Y"}],
        },
    )

    assert response.status_code == 422
    response_json = response.json()
    assert len(response_json["detail"]) == 1
    error = response_json["detail"][0]
    assert error["type"] == "string_pattern_mismatch"
    assert error["loc"] == ["body", "how"]
    assert error["msg"].startswith("String should match pattern")
    assert error["input"] == "invalid"


@pytest.mark.usefixtures("_patch_get_circuit_config_path")
@pytest.mark.parametrize(
    "params, expected",
    [
        (
            {"population_name": "default"},
            {"default": [[0], [1]]},
        ),
        (
            {"population_name": "default2"},
            {"default2": [[0, 1], [1, 3]]},
        ),
    ],
)
async def test_sample(api_client_with_auth, circuit_id, input_path, tmp_path, params, expected):
    response = await api_client_with_auth.post(
        "/circuit/sample",
        json={
            "circuit_id": circuit_id,
            "sampling_ratio": 0.5,
            "seed": 103,  # affects the randomly selected ids
            **params,
        },
    )

    assert response.status_code == 200
    output_path = tmp_path / "nodes.h5"
    output_path.write_bytes(response.content)
    ns = libsonata.NodeStorage(output_path)
    assert ns.population_names == set(expected)
    for population_name, (ids1, ids2) in expected.items():
        node_population = ns.open_population(population_name)
        node_population_orig = _get_node_population(input_path, population_name)
        assert node_population.size == len(ids1) == len(ids2)
        _assert_populations_equal(node_population, node_population_orig, ids1, ids2)


@pytest.mark.usefixtures("_patch_get_circuit_config_path")
async def test_count_all(api_client_with_auth, circuit_id):
    response = await api_client_with_auth.get("/circuit/count", params={"circuit_id": circuit_id})

    assert response.status_code == 200
    assert response.json() == {
        "nodes": {"populations": {"default": {"size": 3}, "default2": {"size": 4}}}
    }


@pytest.mark.usefixtures("_patch_get_circuit_config_path")
async def test_count_population(api_client_with_auth, circuit_id):
    response = await api_client_with_auth.get(
        "/circuit/count",
        params={
            "circuit_id": circuit_id,
            "population_name": "default",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"nodes": {"populations": {"default": {"size": 3}}}}


@pytest.mark.usefixtures("_patch_get_circuit_config_path")
async def test_attribute_names(api_client_with_auth, circuit_id):
    response = await api_client_with_auth.get(
        "/circuit/attribute_names",
        params={
            "circuit_id": circuit_id,
            "population_name": "default",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "populations": {
            "default": [
                "layer",
                "model_template",
                "model_type",
                "morphology",
                "mtype",
                "region",
                "rotation_angle_xaxis",
                "rotation_angle_yaxis",
                "rotation_angle_zaxis",
                "x",
                "y",
                "z",
                "@dynamics:holding_current",
            ]
        }
    }


@pytest.mark.usefixtures("_patch_get_circuit_config_path")
async def test_attribute_dtypes(api_client_with_auth, circuit_id):
    response = await api_client_with_auth.get(
        "/circuit/attribute_dtypes",
        params={
            "circuit_id": circuit_id,
            "population_name": "default",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "populations": {
            "default": {
                "@dynamics:holding_current": "float64",
                "layer": "category",
                "model_template": "category",
                "model_type": "category",
                "morphology": "object",
                "mtype": "category",
                "region": "category",
                "rotation_angle_xaxis": "float64",
                "rotation_angle_yaxis": "float64",
                "rotation_angle_zaxis": "float64",
                "x": "float32",
                "y": "float32",
                "z": "float32",
            }
        }
    }


@pytest.mark.usefixtures("_patch_get_circuit_config_path")
async def test_attribute_values(api_client_with_auth, circuit_id):
    response = await api_client_with_auth.get(
        "/circuit/attribute_values",
        params={
            "circuit_id": circuit_id,
            "population_name": "default",
            "attribute_names": ["mtype", "morphology"],
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "populations": {
            "default": {
                "mtype": ["L2_X", "L6_Y"],
                "morphology": ["morph-A", "morph-B", "morph-C"],
            },
        },
    }


@pytest.mark.usefixtures("_patch_get_circuit_config_path")
async def test_node_sets_get(api_client_with_auth, circuit_id):
    response = await api_client_with_auth.get(
        "/circuit/node_sets", params={"circuit_id": circuit_id}
    )

    assert response.status_code == 200
    assert response.json() == {
        "node_sets": [
            "Layer2",
            "Layer23",
            "Node0_L6_Y",
            "Node12_L6_Y",
            "Node2012",
            "Node2_L6_Y",
            "Population_default",
            "Population_default2",
            "Population_default_L6_Y",
            "Population_default_L6_Y_Node2",
            "combined_Node0_L6_Y__Node12_L6_Y",
            "combined_combined_Node0_L6_Y__Node12_L6_Y__",
        ]
    }


@pytest.mark.usefixtures("_patch_get_circuit_config_path_copy")
async def test_node_sets_get_without_node_sets_file(
    api_client_with_auth, circuit_id, input_path_copy, caplog
):
    with edit_json(input_path_copy) as config:
        config["manifest"]["$BASE_DIR"] = str(TEST_DATA_DIR / "circuit")
        del config["node_sets_file"]

    response = await api_client_with_auth.get(
        "/circuit/node_sets", params={"circuit_id": circuit_id}
    )

    assert response.status_code == 200
    assert response.json() == {"node_sets": []}
    pattern = "Error with node_sets for circuit .*, fallback to empty list"
    assert any(re.search(pattern, rec.msg) for rec in caplog.records), "Log message not found"
