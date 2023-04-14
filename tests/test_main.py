import shutil

from fastapi.testclient import TestClient

import app.main as test_module
from tests.utils import TEST_DATA_DIR, edit_json

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


def test_read_circuit():
    input_path = TEST_DATA_DIR / "circuit" / "circuit_config.json"

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


def test_count_all():
    input_path = TEST_DATA_DIR / "circuit" / "circuit_config.json"

    response = client.get("/circuit/count", params={"input_path": str(input_path)})

    assert response.status_code == 200
    assert response.json() == {
        "nodes": {"populations": {"default": {"size": 3}, "default2": {"size": 4}}}
    }


def test_count_population():
    input_path = TEST_DATA_DIR / "circuit" / "circuit_config.json"

    response = client.get(
        "/circuit/count",
        params={
            "input_path": str(input_path),
            "population_name": ["default"],
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
