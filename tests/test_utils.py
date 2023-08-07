import numpy as np
import pandas as pd
import pytest

import app.utils as test_module
from app.constants import DTYPES


@pytest.mark.parametrize(
    "x, expected",
    [
        ([], []),
        ((), []),
        (None, [None]),
        ("", [""]),
        ("a", ["a"]),
        (["a"], ["a"]),
        (("a",), ["a"]),
    ],
)
def test_ensure_list(x, expected):
    result = test_module.ensure_list(x)

    assert result == expected


def test_ensure_dtypes():
    df = pd.DataFrame({"x": [10], "y": [20], "z": [30], "mtype": ["L2_X"]})
    result = test_module.ensure_dtypes(df, dtypes=DTYPES)

    assert result.dtypes.at["x"] == np.float32
    assert result.dtypes.at["y"] == np.float32
    assert result.dtypes.at["z"] == np.float32
    assert result.dtypes.at["mtype"] == "category"


@pytest.mark.parametrize(
    "modality, expected",
    [
        (None, ["x", "y", "z", "region", "mtype"]),
        ([], ["x", "y", "z", "region", "mtype"]),
        (["mtype"], ["mtype"]),
        (["mtype", "position"], ["mtype", "x", "y", "z"]),
    ],
)
def test_modality_to_attributes(modality, expected):
    result = test_module.modality_to_attributes(modality)

    assert result == expected


@pytest.mark.parametrize(
    "attributes, expected",
    [
        ({}, {}),
        ({"mtype": None, "region": None}, {}),
        ({"mtype": [], "region": []}, {}),
        ({"mtype": ["a"], "region": ["b", "c"]}, {"mtype": ["a"], "region": ["b", "c"]}),
    ],
)
def test_attributes_to_dict(attributes, expected):
    result = test_module.attributes_to_dict(**attributes)

    assert result == expected
