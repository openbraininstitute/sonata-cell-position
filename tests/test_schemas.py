import pytest
from pydantic import ValidationError

import app.schemas as test_module


def test_nexus_config_from_params():
    result = test_module.NexusConfig.from_params(nexus_token="test-token")
    assert isinstance(result, test_module.NexusConfig)
    assert result.token == "test-token"


def test_circuit_ref_from_id():
    result = test_module.CircuitRef(id="test-id", path=None)
    assert isinstance(result, test_module.CircuitRef)

    result = test_module.CircuitRef.from_params(circuit_id="test-id", input_path=None)
    assert isinstance(result, test_module.CircuitRef)


def test_circuit_ref_from_path(input_path):
    result = test_module.CircuitRef(id=None, path=input_path)
    assert isinstance(result, test_module.CircuitRef)

    result = test_module.CircuitRef.from_params(circuit_id=None, input_path=input_path)
    assert isinstance(result, test_module.CircuitRef)


def test_circuit_ref_raises_with_none():
    with pytest.raises(ValidationError, match="circuit id or path must be specified"):
        test_module.CircuitRef(id=None, path=None)


def test_circuit_ref_raises_with_both(input_path):
    with pytest.raises(
        ValidationError, match="circuit id and path cannot be specified at the same time"
    ):
        test_module.CircuitRef(id="test-id", path=input_path)


def test_circuit_ref_raises_with_wrong_extension():
    with pytest.raises(ValidationError, match="Path invalid because of the extension"):
        test_module.CircuitRef(id=None, path="/path/to/nodes.h5")


def test_circuit_ref_raises_with_non_existent_path():
    with pytest.raises(ValidationError, match="Path invalid because non existent"):
        test_module.CircuitRef(id=None, path="/path/to/non/existent/circuit_config.json")
