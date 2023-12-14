import shutil

import libsonata
import pytest
from fastapi.testclient import TestClient

import app.main as test_module
from tests.utils import TEST_DATA_DIR, _assert_populations_equal, _get_node_population, edit_json

client = TestClient(test_module.app)


def test_root_get():
    response = client.get("/", follow_redirects=False)

    assert response.status_code == 302
    assert response.next_request.url.path == "/docs"


def test_health_get():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "OK"}
    assert response.headers["Cache-Control"] == "no-cache"


def test_version_get(monkeypatch):
    project_path = "project/sbo/sonata-cell-position"
    commit_sha = "12345678"
    monkeypatch.setattr(test_module, "PROJECT_PATH", project_path)
    monkeypatch.setattr(test_module, "COMMIT_SHA", commit_sha)

    response = client.get("/version")

    assert response.status_code == 200
    assert response.json() == {"project": project_path, "commit_sha": commit_sha}
    assert response.headers["Cache-Control"] == "no-cache"


def test_read_circuit(input_path):
    response = client.get(
        "/circuit",
        params={
            "input_path": str(input_path),
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


def test_read_circuit_unknown_region_id(input_path):
    response = client.get(
        "/circuit",
        params={
            "input_path": str(input_path),
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


def test_read_circuit_unknown_region_label(input_path):
    response = client.get(
        "/circuit",
        params={
            "input_path": str(input_path),
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


def test_read_circuit_invalid_modality(input_path):
    response = client.get(
        "/circuit",
        params={
            "input_path": str(input_path),
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


def test_query(input_path):
    response = client.post(
        "/circuit/query",
        json={
            "input_path": str(input_path),
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


def test_query_invalid_key(input_path):
    response = client.post(
        "/circuit/query",
        json={
            "input_path": str(input_path),
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


def test_query_invalid_how(input_path):
    response = client.post(
        "/circuit/query",
        json={
            "input_path": str(input_path),
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


@pytest.mark.parametrize(
    "params, expected",
    [
        (
            {"population_name": "default"},
            {"default": [[0], [1]]},
        ),
        (
            {},
            {"default": [[0], [1]], "default2": [[0, 1], [0, 3]]},
        ),
    ],
)
def test_downsample(tmp_path, input_path, params, expected):
    response = client.post(
        "/circuit/downsample",
        json={
            "input_path": str(input_path),
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


def test_count_all(input_path):
    response = client.get("/circuit/count", params={"input_path": str(input_path)})

    assert response.status_code == 200
    assert response.json() == {
        "nodes": {"populations": {"default": {"size": 3}, "default2": {"size": 4}}}
    }


def test_count_population(input_path):
    response = client.get(
        "/circuit/count",
        params={
            "input_path": str(input_path),
            "population_name": "default",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"nodes": {"populations": {"default": {"size": 3}}}}


def test_attribute_names(input_path):
    response = client.get(
        "/circuit/attribute_names",
        params={
            "input_path": str(input_path),
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


def test_attribute_dtypes(input_path):
    response = client.get(
        "/circuit/attribute_dtypes",
        params={
            "input_path": str(input_path),
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
                "mtype": "object",
                "region": "category",
                "rotation_angle_xaxis": "float64",
                "rotation_angle_yaxis": "float64",
                "rotation_angle_zaxis": "float64",
                "x": "float64",
                "y": "float64",
                "z": "float64",
            }
        }
    }


def test_attribute_values(input_path):
    response = client.get(
        "/circuit/attribute_values",
        params={
            "input_path": str(input_path),
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


def test_node_sets_get():
    input_path = TEST_DATA_DIR / "circuit" / "circuit_config.json"

    response = client.get("/circuit/node_sets", params={"input_path": str(input_path)})

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


def test_node_sets_get_without_node_sets_file(tmp_path, caplog):
    src = TEST_DATA_DIR / "circuit"
    dst = tmp_path / src.name
    shutil.copytree(src, dst)
    input_path = dst / "circuit_config.json"
    with edit_json(input_path) as config:
        config["manifest"]["$BASE_DIR"] = str(TEST_DATA_DIR / "circuit")
        del config["node_sets_file"]

    response = client.get("/circuit/node_sets", params={"input_path": str(input_path)})

    assert response.status_code == 200
    assert response.json() == {"node_sets": []}
    msg = "Error with node_sets for circuit %r: %r, fallback to empty list"
    assert any(msg == rec.msg for rec in caplog.records), "Log message not found"
