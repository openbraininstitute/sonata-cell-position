import json
from contextlib import contextmanager
from pathlib import Path

import libsonata
import pandas.testing as pdt
from numpy.testing import assert_array_equal

TEST_DIR = Path(__file__).parent.resolve()
TEST_DATA_DIR = TEST_DIR / "data"


def load_json(json_file, encoding="utf-8"):
    """Load data from json file."""
    return json.loads(json_file.read_text(encoding=encoding))


def dump_json(json_file, data, encoding="utf-8", indent=2, **json_params):
    """Dump data to json file."""
    json_file.write_text(json.dumps(data, indent=indent, **json_params), encoding=encoding)


@contextmanager
def edit_json(json_file, encoding="utf-8"):
    """Context manager within which you can edit a json file.

    Args:
        json_file (Path): path to a json file.
        encoding (str): encoding used to read and write the file.

    Returns:
        Yields a dict instance loaded from `json_file`.
        This instance will be saved after exiting the context manager.
    """
    data = load_json(json_file, encoding=encoding)
    try:
        yield data
    finally:
        dump_json(json_file, data, encoding=encoding)


def _get_node_population(path, population_name):
    if path.suffix == ".json":
        config = libsonata.CircuitConfig.from_file(path)
        node_population = config.node_population(population_name)
    else:
        ns_orig = libsonata.NodeStorage(path)
        node_population = ns_orig.open_population(population_name)
    return node_population


def _assert_populations_equal(pop1, pop2, ids1, ids2):
    assert len(ids1) == len(ids2)
    assert pop1.attribute_names == pop2.attribute_names
    assert pop1.dynamics_attribute_names == pop2.dynamics_attribute_names
    assert pop1.enumeration_names == pop2.enumeration_names
    for name in sorted(pop1.attribute_names):
        assert_array_equal(
            pop1.get_attribute(name, ids1),
            pop2.get_attribute(name, ids2),
            err_msg=f"Different {name}",
        )
    for name in sorted(pop1.dynamics_attribute_names):
        assert_array_equal(
            pop1.get_dynamics_attribute(name, ids1),
            pop2.get_dynamics_attribute(name, ids2),
            err_msg=f"Different {name}",
        )
    for name in sorted(pop1.enumeration_names):
        assert_array_equal(
            pop1.get_enumeration(name, ids1),
            pop2.get_enumeration(name, ids2),
            err_msg=f"Different {name}",
        )


def assert_frame_equal(*args, check_categorical=False, **kwargs):
    """Same as pandas.testing.assert_frame_equal, but do not check categories by default."""
    pdt.assert_frame_equal(*args, check_categorical=check_categorical, **kwargs)
