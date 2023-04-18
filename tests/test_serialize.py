import io

import pandas as pd
import pyarrow as pa
import pytest
from pandas.testing import assert_frame_equal

import app.serialize as test_module
from tests.utils import load_json


@pytest.mark.parametrize(
    "how, orient, expected",
    [
        ("json", None, {"x": {"0": 10}, "y": {"0": 20}, "z": {"0": 30}, "mtype": {"0": "L2_X"}}),
        (
            "json",
            "columns",
            {"x": {"0": 10}, "y": {"0": 20}, "z": {"0": 30}, "mtype": {"0": "L2_X"}},
        ),
        (
            "json",
            "split",
            {"columns": ["x", "y", "z", "mtype"], "index": [0], "data": [[10, 20, 30, "L2_X"]]},
        ),
        ("json", "records", [{"x": 10, "y": 20, "z": 30, "mtype": "L2_X"}]),
        ("json", "index", {"0": {"x": 10, "y": 20, "z": 30, "mtype": "L2_X"}}),
    ],
)
def test_write_json(tmp_path, how, orient, expected):
    how = how if orient is None else f"{how}:{orient}"
    df = pd.DataFrame({"x": [10], "y": [20], "z": [30], "mtype": ["L2_X"]})
    output_path = tmp_path / "output.json"

    test_module.write(
        df=df,
        modality_names=["position", "mtype"],
        output_path=output_path,
        how=how,
    )

    result_data = load_json(output_path)
    result_df = pd.read_json(output_path, orient=orient)
    assert result_data == expected
    assert_frame_equal(result_df, df)


def test_write_arrow(tmp_path):
    df = pd.DataFrame({"x": [10], "y": [20], "z": [30], "mtype": ["L2_X"]})
    output_path = tmp_path / "output.arrow"

    test_module.write(
        df=df,
        modality_names=["position", "mtype"],
        output_path=output_path,
        how="arrow",
    )

    with open(output_path, "rb") as source:
        with pa.ipc.open_file(source) as reader:
            result_df = reader.read_pandas()
    assert_frame_equal(result_df, df)


def test_write_parquet(tmp_path):
    df = pd.DataFrame({"x": [10], "y": [20], "z": [30], "mtype": ["L2_X"]})
    output_path = tmp_path / "output.parquet"

    test_module.write(
        df=df,
        modality_names=["position", "mtype"],
        output_path=output_path,
        how="parquet",
    )

    result_df = pd.read_parquet(output_path, engine="pyarrow")
    assert_frame_equal(result_df, df)


def test_write_rab_parquet(tmp_path):
    import randomaccessbuffer as rab

    df = pd.DataFrame({"x": [10], "y": [20], "z": [30], "mtype": ["L2_X"]})
    output_path = tmp_path / "output.rab"

    test_module.write(
        df=df,
        modality_names=["position", "mtype"],
        output_path=output_path,
        how="rab:parquet",
    )

    rab_instance = rab.RandomAccessBuffer()
    rab_instance.read(output_path)
    dataset_ids = rab_instance.listDatasets()
    assert dataset_ids == ["position", "mtype"]
    # test position
    assert rab_instance.getDatasetType("position") == rab.TYPES.BUFFER
    data, meta = rab_instance.getDataset("position")
    result_df = pd.read_parquet(io.BytesIO(data), engine="pyarrow")
    assert_frame_equal(result_df, df[["x", "y", "z"]])
    # test mtype
    assert rab_instance.getDatasetType("mtype") == rab.TYPES.BUFFER
    data, meta = rab_instance.getDataset("mtype")
    result_df = pd.read_parquet(io.BytesIO(data), engine="pyarrow")
    assert_frame_equal(result_df, df[["mtype"]])


def test_write_rab_rab(tmp_path):
    import randomaccessbuffer as rab

    df = pd.DataFrame({"x": [10], "y": [20], "z": [30], "mtype": ["L2_X"]})
    output_path = tmp_path / "output.rab"

    test_module.write(
        df=df,
        modality_names=["position", "mtype"],
        output_path=output_path,
        how="rab:rab",
    )

    rab_instance = rab.RandomAccessBuffer()
    rab_instance.read(output_path)
    dataset_ids = rab_instance.listDatasets()
    assert dataset_ids == ["position", "mtype"]
    # test position
    assert rab_instance.getDatasetType("position") == rab.TYPES.DATAFRAME
    result_df, meta = rab_instance.getDataset("position")
    assert isinstance(result_df, pd.DataFrame)
    assert_frame_equal(result_df, df[["x", "y", "z"]])
    # test mtype
    assert rab_instance.getDatasetType("mtype") == rab.TYPES.DATAFRAME
    result_df, meta = rab_instance.getDataset("mtype")
    assert isinstance(result_df, pd.DataFrame)
    assert_frame_equal(result_df, df[["mtype"]])
