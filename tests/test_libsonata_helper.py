import libsonata
import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

import app.libsonata_helper as test_module


def test_get_node_population(input_path):
    result = test_module.get_node_population(input_path, population_name="default")
    assert isinstance(result, libsonata.NodePopulation)
    assert result.name == "default"


def test_get_node_population_raises(input_path):
    with pytest.raises(
        ValueError, match="population_name must be specified when there are multiple populations"
    ):
        test_module.get_node_population(input_path)


def test_get_node_populations(input_path):
    result = test_module.get_node_populations(input_path)
    result = list(result)
    assert len(result) == 2
    for node_population, name in zip(result, ["default", "default2"]):
        assert isinstance(node_population, libsonata.NodePopulation)
        assert node_population.name == name


@pytest.mark.parametrize(
    "query_list, expected_data, expected_ids",
    [
        (
            None,
            [
                [401.0, 402.0, 403.0, "L7_X", 1.1],
                [501.0, 502.0, 503.0, "L8_Y", 1.2],
                [601.0, 602.0, 603.0, "L8_Y", 1.3],
                [701.0, 702.0, 703.0, "L9_Z", 1.4],
            ],
            [0, 1, 2, 3],
        ),
        (
            [],
            [
                [401.0, 402.0, 403.0, "L7_X", 1.1],
                [501.0, 502.0, 503.0, "L8_Y", 1.2],
                [601.0, 602.0, 603.0, "L8_Y", 1.3],
                [701.0, 702.0, 703.0, "L9_Z", 1.4],
            ],
            [0, 1, 2, 3],
        ),
        (
            [{}],
            [
                [401.0, 402.0, 403.0, "L7_X", 1.1],
                [501.0, 502.0, 503.0, "L8_Y", 1.2],
                [601.0, 602.0, 603.0, "L8_Y", 1.3],
                [701.0, 702.0, 703.0, "L9_Z", 1.4],
            ],
            [0, 1, 2, 3],
        ),
        (
            [{"mtype": "L8_Y"}],
            [
                [501.0, 502.0, 503.0, "L8_Y", 1.2],
                [601.0, 602.0, 603.0, "L8_Y", 1.3],
            ],
            [1, 2],
        ),
        (
            [{"mtype": ["L8_Y", "L9_Z"], "morphology": "morph-E"}],
            [
                [501.0, 502.0, 503.0, "L8_Y", 1.2],
            ],
            [1],
        ),
        (
            [{"mtype": "L7_X"}, {"morphology": "morph-F"}],
            [
                [401.0, 402.0, 403.0, "L7_X", 1.1],
                [601.0, 602.0, 603.0, "L8_Y", 1.3],
            ],
            [0, 2],
        ),
    ],
)
def test_query_from_file(input_path, query_list, expected_data, expected_ids):
    result = test_module.query_from_file(
        input_path=input_path,
        population_name="default2",
        query_list=query_list,
        attributes=["x", "y", "z", "mtype", "@dynamics:holding_current"],
        sampling_ratio=1.0,
        seed=0,
        sort=True,
        with_node_ids=True,
    )
    assert isinstance(result, pd.DataFrame)
    expected = pd.DataFrame(
        data=expected_data,
        columns=["x", "y", "z", "mtype", "@dynamics:holding_current"],
        index=expected_ids,
    )
    assert_frame_equal(result, expected)


def test_query_from_file_with_attributes_none(input_path):
    result = test_module.query_from_file(
        input_path=input_path,
        population_name="default2",
        query_list=[{"morphology": "morph-E"}],
        attributes=None,
        sampling_ratio=1.0,
        seed=0,
        sort=True,
        with_node_ids=True,
    )
    assert isinstance(result, pd.DataFrame)
    expected = pd.DataFrame(
        data=[
            [
                8,
                "hoc:small_bio",
                "biophysical",
                "morph-E",
                "L8_Y",
                "B",
                11,
                0.0,
                0.0,
                0.0,
                501.0,
                502.0,
                503.0,
                1.2,
            ]
        ],
        columns=[
            "layer",
            "model_template",
            "model_type",
            "morphology",
            "mtype",
            "other1",
            "other2",
            "rotation_angle_xaxis",
            "rotation_angle_yaxis",
            "rotation_angle_zaxis",
            "x",
            "y",
            "z",
            "@dynamics:holding_current",
        ],
        index=[1],
    )
    assert_frame_equal(result, expected)


def test_query_from_file_with_attributes_empty_list(input_path):
    result = test_module.query_from_file(
        input_path=input_path,
        population_name="default2",
        query_list=[{"morphology": "morph-E"}],
        attributes=[],
        sampling_ratio=1.0,
        seed=0,
        sort=True,
        with_node_ids=True,
    )
    assert isinstance(result, pd.DataFrame)
    expected = pd.DataFrame(index=[1])
    assert_frame_equal(result, expected)


@pytest.mark.parametrize("missing", ["unknown", "@dynamics:unknown"])
def test_query_from_file_with_missing_attribute(input_path, missing):
    pop = "default2"
    with pytest.raises(RuntimeError, match=f"Attribute not found in population {pop}: {missing}"):
        test_module.query_from_file(
            input_path=input_path,
            population_name=pop,
            query_list=[],
            attributes=["x", "y", "z", "mtype", missing],
            sampling_ratio=1.0,
            seed=0,
            sort=True,
            with_node_ids=True,
        )
