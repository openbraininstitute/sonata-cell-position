import pytest

import app.brain_region as test_module
from app.errors import ClientError


@pytest.mark.parametrize(
    ("region_id", "expected"),
    [
        ("http://api.brain-map.org/api/v2/data/Structure/8", 8),
        ("http://api.brain-map.org/api/v2/data/Structure/12345", 12345),
    ],
)
def test_region_id_to_int(region_id, expected):
    result = test_module._region_id_to_int(region_id)
    assert result == expected


@pytest.mark.parametrize(
    "region_id",
    [
        "http://api.brain-map.org/api/v2/data/Structure/",
        "http://api.brain-map.org/api/v2/data/Structure/abc",
        "http://api.brain-map.org/api/v2/data/Structure/12345abc",
        "12345",
    ],
)
def test_region_id_to_int_raises(region_id):
    with pytest.raises(ClientError, match="Invalid region id format"):
        test_module._region_id_to_int(region_id)


def test_load_alternative_region_map(alternative_brain_region_file):
    result = test_module.load_alternative_region_map(alternative_brain_region_file)
    assert result[
        "http://bbp.epfl.ch/neurosciencegraph/ontologies/core/brainregion/Isocortex_L4"
    ] == [
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
    assert len(result) == 29
