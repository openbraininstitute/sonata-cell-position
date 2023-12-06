import pytest

import app.service as test_module
from app.errors import CircuitError


@pytest.mark.parametrize(
    "regions, expected",
    [
        ([], []),
        (["838"], ["SSp-n2/3", "SSp-n2", "SSp-n3"]),
        (["SSp-n2/3"], ["SSp-n2/3", "SSp-n2", "SSp-n3"]),
        (["838", "SSp-n2/3"], ["SSp-n2/3", "SSp-n2", "SSp-n3"]),
    ],
)
def test_region_acronyms(regions, expected):
    result = test_module._region_acronyms(regions)

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
def test_region_acronyms_not_found(regions):
    with pytest.raises(CircuitError, match="No region ids found with region"):
        test_module._region_acronyms(regions)
