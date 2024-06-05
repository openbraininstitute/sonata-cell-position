import importlib.resources
import shutil
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import voxcell
from requests import HTTPError

import app.nexus as test_module
from app.errors import ClientError
from tests.utils import assert_cache, clear_cache


@pytest.fixture
def hierarchy(tmp_path):
    ref = importlib.resources.files("app") / "data" / "hierarchy.json"
    with importlib.resources.as_file(ref) as path:
        return shutil.copy(path, tmp_path)


def test_load_cached_resource(nexus_config):
    resource_id = "test-resource-id"
    nexus_config.token = "test-token"
    resource = MagicMock()
    resource_class = MagicMock()
    resource_class.from_id.return_value = resource

    with clear_cache(test_module.load_cached_resource) as tested_func:
        result = tested_func(resource_class, resource_id, nexus_config=nexus_config)
        assert_cache(tested_func, hits=0, misses=1, currsize=1)
        assert result is resource
        assert resource_class.from_id.call_count == 1

        result = tested_func(resource_class, resource_id, nexus_config=nexus_config)
        assert_cache(tested_func, hits=1, misses=1, currsize=1)
        assert result is resource
        assert resource_class.from_id.call_count == 1


def test_load_cached_resource_with_nexus_error(nexus_config):
    resource_id = "test-resource-id"
    nexus_config.token = "test-token"
    resource_class = MagicMock()
    resource_class.from_id.side_effect = HTTPError("401 Client Error: Unauthorized for url")

    with clear_cache(test_module.load_cached_resource) as tested_func:
        with pytest.raises(ClientError, match="401 Client Error: Unauthorized for url"):
            tested_func(resource_class, resource_id, nexus_config=nexus_config)
        assert_cache(tested_func, hits=0, misses=1, currsize=0)


def test_load_cached_resource_with_resource_id_none(nexus_config):
    resource_id = None
    nexus_config.token = "test-token"
    resource_class = MagicMock()
    resource_class.from_id.side_effect = HTTPError("401 Client Error: Unauthorized for url")

    with clear_cache(test_module.load_cached_resource) as tested_func:
        with pytest.raises(ClientError, match="Resource id must be set"):
            tested_func(resource_class, resource_id, nexus_config=nexus_config)
        assert_cache(tested_func, hits=0, misses=1, currsize=0)


def test_load_cached_resource_with_nexus_token_none(nexus_config):
    resource_id = "test-resource-id"
    nexus_config.token = None
    resource_class = MagicMock()
    resource_class.from_id.side_effect = HTTPError("401 Client Error: Unauthorized for url")

    with clear_cache(test_module.load_cached_resource) as tested_func:
        with pytest.raises(ClientError, match="Nexus token must be set"):
            tested_func(resource_class, resource_id, nexus_config=nexus_config)
        assert_cache(tested_func, hits=0, misses=1, currsize=0)


def test_load_cached_resource_with_result_none(nexus_config):
    resource_id = "test-resource-id"
    nexus_config.token = "test-token"
    resource_class = MagicMock()
    resource_class.from_id.return_value = None

    with clear_cache(test_module.load_cached_resource) as tested_func:
        with pytest.raises(ClientError, match="Resource not found"):
            tested_func(resource_class, resource_id, nexus_config=nexus_config)
        assert_cache(tested_func, hits=0, misses=1, currsize=0)


def test_load_cached_region_map(nexus_config, hierarchy):
    resource = MagicMock()
    resource.distribution = [
        MagicMock(encodingFormat="application/ld+json"),
        MagicMock(encodingFormat="application/json", download=MagicMock(return_value=hierarchy)),
    ]

    with clear_cache(test_module.load_cached_region_map) as tested_func:
        result_1 = tested_func(resource, nexus_config=nexus_config)
        assert_cache(tested_func, hits=0, misses=1, currsize=1)
        assert isinstance(result_1, voxcell.RegionMap)
        assert resource.distribution[0].download.call_count == 0
        assert resource.distribution[1].download.call_count == 1

        result_2 = tested_func(resource, nexus_config=nexus_config)
        assert_cache(tested_func, hits=1, misses=1, currsize=1)
        assert isinstance(result_2, voxcell.RegionMap)
        assert resource.distribution[0].download.call_count == 0
        assert resource.distribution[1].download.call_count == 1

        assert result_1 is result_2


def test_load_cached_region_map_hierarchy_not_found(nexus_config, hierarchy):
    resource = MagicMock()
    resource.distribution = [
        MagicMock(encodingFormat="application/ld+json"),
    ]

    with clear_cache(test_module.load_cached_region_map) as tested_func:
        with pytest.raises(ClientError, match="Hierarchy json not found for id"):
            tested_func(resource, nexus_config=nexus_config)
        assert_cache(tested_func, hits=0, misses=1, currsize=0)
        assert resource.distribution[0].download.call_count == 0


def test_get_circuit_config_path():
    path = "/path/to/circuit_config.json"
    resource = MagicMock()
    resource.circuitConfigPath.get_url_as_path.return_value = path

    result = test_module.get_circuit_config_path(resource)
    assert result == Path(path)


def test_get_circuit_config_path_with_missing_attribute():
    resource = MagicMock()
    resource.circuitConfigPath = None

    with pytest.raises(
        ClientError, match="Error in resource.*object has no attribute 'get_url_as_path'"
    ):
        test_module.get_circuit_config_path(resource)
