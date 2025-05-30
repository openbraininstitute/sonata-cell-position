"""Service functions."""

import functools
import importlib.resources
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from voxcell import RegionMap

from app.brain_region import load_alternative_region_map
from app.config import settings
from app.constants import CIRCUITS
from app.errors import CircuitError, ClientError
from app.libsonata_helper import (
    get_node_population_name,
    get_node_populations,
    get_node_sets,
    query_from_file,
    sample_nodes,
)
from app.logger import L
from app.schemas import CircuitParams, CircuitRef, UserContext


def _get_circuit_config_path_from_id(circuit_id) -> Path:
    """Return the circuit config path for the given circuit id.

    Args:
        circuit_id: circuit id.

    Returns:
        The path to the circuit.
    """
    try:
        path = CIRCUITS[circuit_id]
    except KeyError:
        msg = f"Circuit id not found: {circuit_id!r}"
        raise ClientError(msg) from None
    return Path(path)


def get_circuit_config_path(circuit_ref: CircuitRef, user_context: UserContext) -> Path:
    """Return the circuit config path of the given circuit."""
    if circuit_ref.path:
        return circuit_ref.path
    return _get_circuit_config_path_from_id(circuit_ref.id)


def get_single_node_population_name(circuit_ref: CircuitRef, user_context: UserContext) -> str:
    """Return the single node population of the circuit, or raise an error if there are many."""
    path = get_circuit_config_path(circuit_ref, user_context=user_context)
    return get_node_population_name(path)


@functools.cache
def get_bundled_region_map() -> RegionMap:
    """Return the bundled region map."""
    L.info("Loading bundled region map")
    ref = importlib.resources.files("app") / "data" / settings.HIERARCHY_BUNDLED_FILE
    with importlib.resources.as_file(ref) as path:
        return RegionMap.load_json(path.absolute())


@functools.cache
def get_bundled_alternative_region_map() -> dict:
    """Return the bundled region map."""
    L.info("Loading bundled alternative region map")
    ref = importlib.resources.files("app") / "data" / settings.BRAIN_REGION_ONTOLOGY_BUNDLED_FILE
    with importlib.resources.as_file(ref) as path:
        return load_alternative_region_map(path)


def get_region_map(circuit_ref: CircuitRef, user_context: UserContext) -> RegionMap:
    """Return the region map used for the given circuit."""
    # TODO: call entitycore to get the region_map associated with the specific circuit
    return get_bundled_region_map()


def get_alternative_region_map(circuit_ref: CircuitRef, user_context: UserContext) -> dict:
    """Return the region map used for the given circuit."""
    # TODO: call entitycore to get the alternative_region_map associated with the specific circuit
    return get_bundled_alternative_region_map()


def _region_acronyms(
    regions: list[str], region_map: RegionMap, alternative_region_map: dict
) -> list[str]:
    """Return acronyms of regions in `regions`."""
    result: set[str] = set()
    for region in regions:
        try:
            ids = region_map.find(int(region), "id", with_descendants=True)
        except ValueError:
            ids = region_map.find(region, "acronym", with_descendants=True)
        if not ids:
            ids = alternative_region_map.get(region)
        if not ids:
            raise CircuitError(f"No region ids found with region {region!r}")
        result.update(region_map.get(id_, "acronym") for id_ in ids)
    return list(result)


def export(
    circuit_params: CircuitParams,
    queries: list[dict[str, Any]] | None,
    node_set: str | None,
    write: Callable[[pd.DataFrame], None],
) -> None:
    """Return a DataFrame of nodes attributes.

    Args:
        circuit_params: instance of CircuitParams,
        queries: list of query dictionaries.
        node_set: name of a node_set to load.
        write: function accepting the DataFrame to write as a single parameter.
    """
    queries = [
        (
            {
                **query,
                "region": _region_acronyms(
                    regions=query["region"],
                    region_map=circuit_params.region_map,
                    alternative_region_map=circuit_params.alternative_region_map,
                ),
            }
            if "region" in query
            else query
        )
        for query in queries or []
    ]
    key = circuit_params.key
    df = query_from_file(
        input_path=key.circuit_config_path,
        population_name=key.population_name,
        sampling_ratio=key.sampling_ratio,
        queries=queries,
        node_set=node_set,
        attributes=key.attributes,
        seed=key.seed,
        sort=False,
        with_node_ids=False,
    )
    write(df)


def count(input_path: Path, population_name: str | None = None) -> dict:
    """Return the number of nodes per population in the given circuit.

    Args:
        input_path: path to the circuit config file.
        population_name: optional name of the node population.

    Returns:
        A dict containing the number of nodes per population.

    """
    population_names = [population_name] if population_name else None
    populations = {
        node_population.name: {"size": node_population.size}
        for node_population in get_node_populations(input_path, population_names)
    }
    return {"nodes": {"populations": populations}}


def get_attribute_names(
    input_path: Path,
    population_name: str | None = None,
) -> dict:
    """Return the attribute names per node population in the given circuit.

    Args:
        input_path: path to the circuit config file.
        population_name: optional name of the node population.

    Returns:
        A dict containing the attribute names per node population.

    Examples:
        {
          "populations": {
            "population_0": [
              "morphology",
              "mtype",
              "x",
              "y",
              "z",
            ]
          }
        }
    """
    population_names = [population_name] if population_name else None
    return {
        "populations": {
            node_population.name: query_from_file(
                input_path=input_path,
                population_name=node_population.name,
                sort=False,
                with_node_ids=False,
                ids=np.array([]),
            ).columns.to_list()
            for node_population in get_node_populations(input_path, population_names)
        }
    }


def get_attribute_dtypes(
    input_path: Path,
    population_name: str | None = None,
) -> dict:
    """Return the data types of each attribute per node population in the given circuit.

    Args:
        input_path: path to the circuit config file.
        population_name: optional name of the node population.

    Returns:
        A dict containing the data types of each attribute per node population.

    Examples:
        {
          "populations": {
            "population_0": {
              "morphology": "object",
              "mtype": "category",
              "x": "float64",
              "y": "float64",
              "z": "float64",
            }
          }
        }
    """
    population_names = [population_name] if population_name else None
    return {
        "populations": {
            node_population.name: query_from_file(
                input_path=input_path,
                population_name=node_population.name,
                sort=False,
                with_node_ids=False,
                ids=np.array([]),
            )
            .dtypes.apply(str)
            .to_dict()
            for node_population in get_node_populations(input_path, population_names)
        }
    }


def get_attribute_values(
    input_path: Path,
    population_name: str | None = None,
    attribute_names: list[str] | None = None,
) -> dict:
    """Return the unique values of each attribute per population in the given circuit.

    Only the attributes having data type string or category (enum) are considered.

    Args:
        input_path: path to the circuit config file.
        population_name: optional name of the node population.
        attribute_names: optional list of attributes to retrieve.

    Returns:
        A dict containing the unique values of each attribute per node population.

    Examples:
        {
          "populations": {
            "population_0": {
              "mtype": [
                "L2_X",
                "L6_Y"
              ],
              "morphology": [
                "morph-A",
                "morph-B",
                "morph-C"
              ]
            }
          }
        }
    """
    population_names = [population_name] if population_name else None
    populations: dict[str, dict[str, list[str]]] = {}
    for node_population in get_node_populations(input_path, population_names):
        df = query_from_file(
            input_path=input_path,
            population_name=node_population.name,
            attributes=attribute_names,
            sort=False,
            with_node_ids=False,
            ids=np.array([]),
            dtypes=False,
        )
        props = populations[node_population.name] = {}
        for attribute_name in df.columns:
            if df.dtypes[attribute_name] == "category":
                props[attribute_name] = (
                    df[attribute_name].cat.categories.drop_duplicates().to_list()
                )
            elif df.dtypes[attribute_name] == "object":
                # potentially slow, because it needs to load the full column
                props[attribute_name] = (
                    query_from_file(
                        input_path=input_path,
                        population_name=node_population.name,
                        attributes=[attribute_name],
                        sort=False,
                        with_node_ids=False,
                        dtypes=False,
                    )[attribute_name]
                    .drop_duplicates()
                    .sort_values()
                    .to_list()
                )
    return {"populations": populations}


def sample(
    user_context: UserContext,
    circuit_ref: CircuitRef,
    output_path: Path,
    population_name: str,
    sampling_ratio: float = 0.01,
    seed: int = 0,
    attributes: Iterable[str] | None = None,
) -> None:
    """Sample a node file."""
    path = get_circuit_config_path(circuit_ref, user_context=user_context)
    sample_nodes(
        input_path=path,
        output_path=output_path,
        population_name=population_name,
        sampling_ratio=sampling_ratio,
        seed=seed,
        attributes=attributes,
    )


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
        L.warning(
            "Error with node_sets for circuit {!r}: {!r}, fallback to empty list", input_path, ex
        )
        node_sets = []

    return {"node_sets": node_sets}
