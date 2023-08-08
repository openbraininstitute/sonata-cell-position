"""Service functions."""
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import h5py
import libsonata
import numpy as np
import pandas as pd
from numpy.random import default_rng

from app.constants import DTYPES, REGION_MAP, SAMPLING_RATIO
from app.errors import CircuitError
from app.libsonata_helper import get_node_populations, get_node_sets, query_from_file
from app.logger import L
from app.utils import ensure_dtypes


def _region_acronyms(regions: list[str]) -> list[str]:
    """Return acronyms of regions in `regions`."""
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
    queries: list[dict[str, Any]] | None = None,
    node_set: str | None = None,
    attributes: list[str] | None = None,
    seed: int = 0,
) -> pd.DataFrame:
    """Return a DataFrame of nodes attributes.

    Args:
        input_path: path to the circuit config file, or nodes file.
        population_name: name of the node population.
        sampling_ratio: sampling_ratio of cells to be considered, expressed as float (0.01 = 1%).
        queries: list of query dictionaries.
        node_set: name of a node_set to load.
        attributes: list of attributes to export.
        seed: random number generator seed.

    Returns:
        The resulting DataFrame.

    """
    queries = [
        {**query, "region": _region_acronyms(query["region"])} if "region" in query else query
        for query in queries or []
    ]
    df = query_from_file(
        input_path=input_path,
        population_name=population_name,
        sampling_ratio=sampling_ratio,
        queries=queries,
        node_set=node_set,
        attributes=attributes,
        seed=seed,
        sort=False,
        with_node_ids=False,
    )
    # ensure the desired dtypes (for example, to convert from float64 to float32)
    df = ensure_dtypes(df, dtypes=DTYPES)
    return df


def count(input_path: Path, population_names: list[str] | None = None) -> dict:
    """Return the number of nodes per population in the given circuit.

    Args:
        input_path: path to the circuit config file, or nodes file.
        population_names: names of the node populations.

    Returns:
        A dict containing the number of nodes per population.

    """
    populations = {}
    for node_population in get_node_populations(input_path, population_names):
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
        for node_population in get_node_populations(input_path, population_names):
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


def get_node_set_names(input_path: Path) -> dict:
    """Return the names of the available node_sets.

    Args:
        input_path: path to the circuit config file.

    Returns:
        A dict containing the node_sets from the circuit_config.
    """
    try:
        ns = get_node_sets(input_path)
        node_sets = sorted(ns.names)
    except CircuitError as ex:
        L.warning("Error with node_sets for circuit %r: %r, fallback to empty list", input_path, ex)
        node_sets = []

    return {"node_sets": node_sets}
