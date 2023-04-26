"""Libsonata helper functions."""
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

import libsonata
import numpy as np
import pandas as pd
from numpy.random import default_rng

from app.constants import DTYPES, SAMPLING_RATIO
from app.logger import L
from app.utils import ensure_dtypes, ensure_list


def get_node_population(path: Path, population_name: str | None = None) -> libsonata.NodePopulation:
    """Load and return a libsonata node population.

    Args:
        path: path to the circuit config file, or nodes file.
        population_name: name of the node population to load.

    Returns:
        The loaded node population.

    """
    population_names = {population_name} if population_name else None
    node_populations = list(get_node_populations(path, population_names))
    if len(node_populations) > 1 and not population_name:
        # population_names is an unordered set, so we don't know which one to choose
        raise ValueError("population_name must be specified when there are multiple populations")
    if len(node_populations) != 1:
        raise RuntimeError("Exactly one node population should have been selected")
    return node_populations[0]


def get_node_populations(
    path: Path, population_names: Iterable[str] | None = None
) -> Iterator[libsonata.NodePopulation]:
    """Load and yield libsonata node populations.

    Args:
        path: path to the circuit config file, or nodes file.
        population_names: names of the node populations to load, or None to load all of them.

    Yields:
        The loaded node populations. The populations are sorted by name to ensure reproducibility
        when working with multiple populations and specific seeds.

    """
    if path.suffix == ".json":
        # sonata circuit config
        config = libsonata.CircuitConfig.from_file(path)
        for population_name in sorted(population_names or config.node_populations):
            yield config.node_population(population_name)
    else:
        # hdf5 nodes file
        ns = libsonata.NodeStorage(path)
        for population_name in sorted(population_names or ns.population_names):
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
    df = ensure_dtypes(df, dtypes=DTYPES)
    return df
