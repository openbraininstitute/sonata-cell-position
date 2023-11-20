import shutil

import libsonata
import pytest
from fastapi.testclient import TestClient

import app.main as test_module
from tests.utils import TEST_DATA_DIR, _assert_populations_equal, _get_node_population, edit_json

client = TestClient(test_module.app)


def test_root_get(monkeypatch):
    project_path = "project/sbo/sonata-cell-position"
    monkeypatch.setattr(test_module, "PROJECT_PATH", project_path)

    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"project": project_path, "status": "OK"}


def test_version_get(monkeypatch):
    project_path = "project/sbo/sonata-cell-position"
    commit_sha = "12345678"
    monkeypatch.setattr(test_module, "PROJECT_PATH", project_path)
    monkeypatch.setattr(test_module, "COMMIT_SHA", commit_sha)

    response = client.get("/version")

    assert response.status_code == 200
    assert response.json() == {"project": project_path, "commit_sha": commit_sha}


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
    response = client.get(
        "/circuit/downsample",
        params={
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
