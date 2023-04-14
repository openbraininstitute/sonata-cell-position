import voxcell

import app.constants as test_module


def test_region_map():
    assert isinstance(test_module.REGION_MAP, voxcell.RegionMap)
    assert test_module.REGION_MAP.get(997, "acronym") == "root"
