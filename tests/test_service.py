import pytest

import app.service as test_module


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
