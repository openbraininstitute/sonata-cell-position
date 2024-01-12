"""Jobs that can be called from the web service or the CLI."""
from functools import partial
from pathlib import Path
from typing import Any

from app import cache, serialize, service
from app.schemas import CircuitRef, NexusConfig


def read_circuit_job(
    nexus_config: NexusConfig,
    circuit_ref: CircuitRef,
    population_name: str | None,
    sampling_ratio: float,
    attributes: list[str],
    queries: list[dict[str, Any]] | None,
    node_set: str | None,
    seed: int,
    how: str,
    use_cache: bool,
    output_path: Path,
) -> None:
    """Read data from a circuit."""
    # pylint: disable=too-many-arguments
    population_name = population_name or service.get_single_node_population_name(
        circuit_ref, nexus_config=nexus_config
    )
    circuit_params = cache.get_cached_circuit_params(
        nexus_config=nexus_config,
        circuit_ref=circuit_ref,
        population_name=population_name,
        attributes=attributes,
        sampling_ratio=sampling_ratio,
        seed=seed,
        use_circuit_cache=use_cache,
    )
    service.export(
        circuit_params=circuit_params,
        queries=queries,
        node_set=node_set,
        write=partial(serialize.write, attributes=attributes, output_path=output_path, how=how),
    )


def sample_job(
    nexus_config: NexusConfig,
    circuit_ref: CircuitRef,
    output_path: Path,
    population_name: str | None,
    sampling_ratio: float,
    seed: int,
) -> None:
    """Sample a circuit."""
    population_name = population_name or service.get_single_node_population_name(
        circuit_ref, nexus_config=nexus_config
    )
    service.sample(
        nexus_config=nexus_config,
        circuit_ref=circuit_ref,
        output_path=output_path,
        population_name=population_name,
        sampling_ratio=sampling_ratio,
        seed=seed,
    )
