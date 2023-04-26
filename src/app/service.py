"""Service functions."""
from collections.abc import Iterable
from pathlib import Path

import h5py
import libsonata
import numpy as np
import pandas as pd
from numpy.random import default_rng

from app.constants import MODALITIES, REGION_MAP, SAMPLING_RATIO
from app.libsonata_helper import _export_dataframe, get_node_population, get_node_populations
from app.logger import L
from app.utils import modality_names_to_columns


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
    node_population = get_node_population(input_path, population_name)
    modality_names = modality_names or list(MODALITIES)
    columns = modality_names_to_columns(modality_names)
    query = {}
    if mtypes:
        query["mtype"] = mtypes
    if regions:
        query["region"] = _region_acronyms(regions)
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
