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
