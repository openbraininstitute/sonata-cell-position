"""Service functions."""
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

import h5py
import libsonata
import numpy as np
import pandas as pd
from numpy.random import default_rng

from app.constants import DTYPES, MODALITIES, REGION_MAP, SAMPLING_RATIO
from app.logger import L
from app.utils import ensure_list, modality_names_to_columns


def _get_node_population(
    path: Path, population_name: str | None = None
) -> libsonata.NodePopulation:
    """Load and return a libsonata node population.

    Args:
        path: path to the circuit config file, or nodes file.
        population_name: name of the node population to load.

    Returns:
        The loaded node population.

    """
    population_names = {population_name} if population_name else None
    node_populations = list(_get_node_populations(path, population_names))
    if len(node_populations) > 1 and not population_name:
        # population_names is an unordered set, so we don't know which one to choose
        raise ValueError("population_name must be specified when there are multiple populations")
    if len(node_populations) != 1:
        raise RuntimeError("Exactly one node population should have been selected")
    return node_populations[0]


def _get_node_populations(
    path: Path, population_names: Iterable[str] | None = None
) -> Iterator[libsonata.NodePopulation]:
    """Load and yield libsonata node populations.

    Args:
        path: path to the circuit config file, or nodes file.
        population_names: names of the node populations to load, or None to load all of them.

    Yields:
        The loaded node populations.

    """
    if path.suffix == ".json":
        # sonata circuit config
        config = libsonata.CircuitConfig.from_file(path)
        for population_name in population_names or config.node_populations:
            yield config.node_population(population_name)
    else:
        # hdf5 nodes file
        ns = libsonata.NodeStorage(path)
        for population_name in population_names or ns.population_names:
            yield ns.open_population(population_name)


def _filter_by_key(
    node_population: libsonata.NodePopulation,
    df: pd.DataFrame,
    key: str,
    values: list[Any],
    keep: bool,
) -> pd.DataFrame:
    """Filter a DataFrame based on the given key and values.

    Args:
        node_population: libsonata node population instance.
        df: DataFrame with ids as index.
        key: key to filter.
        values: list of values to filter, or empty to not apply any filter.
        keep: if True, add the filtering key as a column to the DataFrame.

    Returns:
        The filtered DataFrame.

    """
    ids = df.index.to_numpy()
    selection = libsonata.Selection(ids)
    attribute: np.ndarray = node_population.get_attribute(key, selection)
    if values:
        mask = np.isin(attribute, values)
        ids = ids[mask]
        attribute = attribute[mask]
        df = df.loc[ids]
    if keep:
        df[key] = attribute
    return df


def _export_dataframe(
    node_population: libsonata.NodePopulation,
    query: dict[str, Any],
    columns: list[str],
    sampling_ratio: float = SAMPLING_RATIO,
    seed: int = 0,
) -> pd.DataFrame:
    """Create and return a DataFrame of attributes filtered as requested.

    Args:
        node_population: libsonata node population instance.
        query: dict of attributes keys and values for filtering, where values can be single or list.
        columns: list of attributes to be exported in the resulting DataFrame.
        sampling_ratio: sampling_ratio of cells to be considered, expressed as float (0.01 = 1%).
        seed: random number generator seed.

    Returns:
        The resulting DataFrame.

    """
    rng = default_rng(seed)
    high = len(node_population)
    ids = rng.choice(high, size=int(high * sampling_ratio), replace=False, shuffle=False)
    ids.sort()
    L.info("Selected random ids: %s", len(ids))
    df = pd.DataFrame(index=ids)
    columns_set = set(columns)
    # Add columns to the filtering query to load all the required attributes.
    # For better performance, keys that filter out more records should go first.
    query = query | {column: None for column in columns if column not in query}
    for key, values in query.items():
        values = ensure_list(values) if values else []
        keep = key in columns_set
        df = _filter_by_key(node_population, df=df, key=key, values=values, keep=keep)
        L.info("Filtered by %s=%s -> %s ids", key, values or "all", len(df))
    # discard the ids in the index
    df.index = pd.RangeIndex(len(df))
    # ensure the desired dtypes
    df = df.astype(DTYPES)
    return df


def _region_acronyms(regions: list[str] | None) -> list[str] | None:
    """Return acronyms of regions in `regions`."""
    if regions is None:
        return None
    result: set[str] = set()
    for region in regions:
        try:
            ids = REGION_MAP.find(int(region), "id", with_descendants=True)
        except ValueError:
            ids = REGION_MAP.find(region, "acronym", with_descendants=True)
        result.update(REGION_MAP.get(id_, "acronym") for id_ in ids)
    return list(result)


def export(
    input_path: Path,
    population_name: str | None = None,
    sampling_ratio: float = SAMPLING_RATIO,
    modality_names: list[str] | None = None,
    regions: list[str] | None = None,
    mtypes: list[str] | None = None,
    seed: int = 0,
) -> pd.DataFrame:
    """Return a DataFrame of nodes attributes.

    Args:
        input_path: path to the circuit config file, or nodes file.
        population_name: name of the node population.
        sampling_ratio: sampling_ratio of cells to be considered, expressed as float (0.01 = 1%).
        modality_names: list of modalities, or None to export every modality.
        regions: list of regions for filtering.
        mtypes: list of mtypes for filtering.
        seed: random number generator seed.

    Returns:
        The resulting DataFrame.

    """
    node_population = _get_node_population(input_path, population_name)
    modality_names = modality_names or list(MODALITIES)
    columns = modality_names_to_columns(modality_names)
    query = {"region": _region_acronyms(regions), "mtype": mtypes}
    return _export_dataframe(
        node_population=node_population,
        sampling_ratio=sampling_ratio,
        query=query,
        columns=columns,
        seed=seed,
    )


def count(input_path: Path, population_names: list[str] | None = None) -> dict:
    """Return the number of nodes per population in the given circuit.

    Args:
        input_path: path to the circuit config file, or nodes file.
        population_names: names of the node populations.

    Returns:
        A dict containing the number of nodes per population.

    """
    populations = {}
    for name in population_names or [None]:  # type: ignore[list-item]
        node_population = _get_node_population(input_path, population_name=name)
        populations[node_population.name] = {"size": node_population.size}
    return {"nodes": {"populations": populations}}


def downsample(
    input_path: Path,
    output_path: Path,
    population_name: str | None,
    sampling_ratio: float = 0.01,
    seed: int = 0,
    attributes: Iterable[str] | None = None,
):
    """Downsample a node file."""

    # pylint: disable=too-many-locals
    def _filter_attributes(names: set[str]):
        if attributes:
            names = names.intersection(attributes)
        yield from sorted(names)

    rng = default_rng(seed)
    str_dt = h5py.special_dtype(vlen=str)
    L.info("Writing file: %s", output_path)
    with h5py.File(output_path, "w") as h5f:
        population_names = {population_name} if population_name else None
        for node_population in _get_node_populations(input_path, population_names):
            high = len(node_population)
            ids = rng.choice(high, size=int(high * sampling_ratio), replace=False, shuffle=False)
            ids.sort()
            selection = libsonata.Selection(ids)
            population_group = h5f.create_group(f"/nodes/{node_population.name}")
            population_group.create_dataset("node_type_id", data=np.full(len(ids), -1))
            group = population_group.create_group("0")
            for name in _filter_attributes(node_population.enumeration_names):
                L.info("Writing enumeration: %s", name)
                data = node_population.enumeration_values(name)
                group.create_dataset(f"@library/{name}", data=data, dtype=str_dt)
                data = node_population.get_enumeration(name, selection)
                group.create_dataset(name, data=data, dtype=data.dtype)
            for name in _filter_attributes(node_population.dynamics_attribute_names):
                L.info("Writing dynamics_attribute: %s", name)
                data = node_population.get_dynamics_attribute(name, selection)
                group.create_dataset(f"dynamics_params/{name}", data=data, dtype=data.dtype)
            for name in _filter_attributes(
                node_population.attribute_names - node_population.enumeration_names
            ):
                L.info("Writing attribute: %s", name)
                data = node_population.get_attribute(name, selection)
                dtype = str_dt if data.dtype == object else data.dtype
                group.create_dataset(name, data=data, dtype=dtype)


def get_node_sets(input_path: Path) -> dict:
    """Return the names of the available node_sets.

    Args:
        input_path: path to the circuit config file.

    Returns:
        A dict containing the node_sets from the circuit_config.

    """
    cc = libsonata.CircuitConfig.from_file(input_path)
    try:
        ns = libsonata.NodeSets.from_file(cc.node_sets_path)
        node_sets = sorted(ns.names)
    except (libsonata.SonataError, RuntimeError) as ex:
        # Possible errors:
        # - RuntimeError: Path `` is not a file (if the key "node_sets_file" is missing)
        # - RuntimeError: Path `/path/to/node_sets.json` is not a file (if the file doesn't exist)
        # - RuntimeError: [json.exception.parse_error.101] parse error... (if the file is invalid)
        L.warning("Error with node_sets for circuit %r: %r, fallback to empty list", input_path, ex)
        node_sets = []
    return {"node_sets": node_sets}
