"""Libsonata helper functions."""
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

import libsonata
import numpy as np
import pandas as pd
from numpy.random import default_rng

from app.constants import DYNAMICS_PREFIX
from app.logger import L
from app.utils import ensure_list


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


def _filter_add_key(
    node_population: libsonata.NodePopulation,
    df: pd.DataFrame,
    key: str,
    values: list[Any],
    keep: bool,
) -> pd.DataFrame:
    """Filter a DataFrame based on the given key and values, and add the key as column.

    Args:
        node_population: libsonata node population instance.
        df: DataFrame with sorted unique ids as index (it may be modified by the function).
        key: key to filter.
        values: list of values to filter, or empty to not apply any filter.
        keep: if True, add the filtering key as a column to the DataFrame.

    Returns:
        The filtered DataFrame (it may be a copy, or the original modified DataFrame).
    """

    def _get_attribute(ids: np.ndarray) -> np.ndarray | pd.Categorical:
        if len(ids) == node_population.size:
            # since the ids are complete and already sorted, this is faster
            selection = libsonata.Selection([(0, len(ids))])
        else:
            selection = libsonata.Selection(ids)
        if key in node_population.enumeration_names:
            return pd.Categorical.from_codes(
                node_population.get_enumeration(key, selection),
                categories=node_population.enumeration_values(key),
            )
        if key in node_population.attribute_names:
            return node_population.get_attribute(key, selection)
        if key.startswith(DYNAMICS_PREFIX):
            stripped_key = key.removeprefix(DYNAMICS_PREFIX)
            if stripped_key in node_population.dynamics_attribute_names:
                return node_population.get_dynamics_attribute(stripped_key, selection)
        raise RuntimeError(f"Attribute not found in population {node_population.name}: {key}")

    ids = df.index.to_numpy()
    attribute = _get_attribute(ids)
    if values:
        if len(values) == 1:
            mask = attribute == values[0]
        else:
            mask = np.isin(attribute, values)
        ids = ids[mask]
        attribute = attribute[mask]
        df = df.loc[ids]
    if keep:
        df[key] = attribute
    return df


def query(
    node_population: libsonata.NodePopulation,
    query_list: list[dict[str, Any]],
    attributes: list[str] | None = None,
    sampling_ratio: float = 1.0,
    seed: int = 0,
    sort: bool = True,
    with_node_ids: bool = True,
) -> pd.DataFrame:
    """Build and return a DataFrame of nodes from the given node_population and queries.

    Args:
        node_population: libsonata node population instance.
        query_list: list of query dictionaries to select the nodes based on attributes.
        attributes: list of attributes to export, or None to export all the attributes.
        sampling_ratio: sampling_ratio of cells to be considered, expressed as float (0.01 = 1%).
        seed: random number generator seed.
        sort: True to sort the result by node id.
        with_node_ids: True to return the node_ids as index of the resulting DataFrame

    Returns:
        pd.DataFrame of nodes with the requested attributes as columns.

    """

    def _init_ids(high: int) -> np.ndarray:
        """Return the sorted initial list of node ids to consider."""
        if sampling_ratio >= 1:
            L.info("Selected all ids: %s", high)
            return np.arange(high)
        rng = default_rng(seed)
        ids = rng.choice(high, size=int(high * sampling_ratio), replace=False, shuffle=False)
        ids.sort()
        L.info("Selected random ids: %s", len(ids))
        return ids

    def _build_df_list(ids: np.ndarray, attributes: list[str]) -> list[pd.DataFrame]:
        """Build and return a list of DataFrames, one for each query."""
        df_list: list[pd.DataFrame] = []
        attributes_set = set(attributes)
        # if query_list is empty, an empty query dict is needed to select the attributes
        for num, query_dict in enumerate(query_list or [{}], 1):
            L.info("Starting %s", f"filter {num}/{len(query_list)}" if query_list else "export")
            if df_list:
                # remove from ids the ids already selected
                ids = np.setdiff1d(ids, df_list[-1].index.to_numpy(), assume_unique=True)
            # Add attributes to the filtering query to load all the required attributes.
            # For better performance, keys that filter out more records should go first.
            query_dict = query_dict | {col: [] for col in attributes if col not in query_dict}
            df = pd.DataFrame(index=ids)
            for key, values in query_dict.items():
                values = ensure_list(values) if values else []
                keep = key in attributes_set
                df = _filter_add_key(node_population, df=df, key=key, values=values, keep=keep)
                L.info("Filtered by %s=%s -> %s ids", key, values or "all", len(df))
            # reorder the columns if needed
            if attributes != df.columns.to_list():
                df = df[attributes]
            df_list.append(df)
        if not df_list:
            raise RuntimeError("No data selected")
        return df_list

    def _calculate():
        ids = _init_ids(len(node_population))
        if attributes is not None:
            selected_attributes = attributes
        else:
            selected_attributes = [
                *sorted(node_population.attribute_names),
                *sorted(f"{DYNAMICS_PREFIX}{n}" for n in node_population.dynamics_attribute_names),
            ]
        df_list = _build_df_list(ids, attributes=selected_attributes)
        if len(df_list) == 1:
            # ids are already sorted
            result = df_list[0]
        else:
            result = pd.concat(df_list)
            result = result.sort_index() if sort else result
        if not with_node_ids:
            # discard the ids in the index
            result.index = pd.RangeIndex(len(result))
        return result

    return _calculate()


def query_from_file(input_path, population_name, **kwargs):
    """Build and return a DataFrame of nodes from the given file, population name, and queries.

    Args:
        input_path: path to the circuit config file, or nodes file.
        population_name: name of the node population.
        **kwargs: arguments to be passed to the query function.

    Returns:
        pd.DataFrame of nodes with the requested attributes as columns.

    """
    node_population = get_node_population(input_path, population_name)
    return query(node_population=node_population, **kwargs)
