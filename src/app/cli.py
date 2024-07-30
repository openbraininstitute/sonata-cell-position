"""CLI entry point."""

import os
import re
from pathlib import Path

import click

from app import jobs
from app.constants import MODALITIES_REGEX
from app.logger import L, configure_logging
from app.schemas import CircuitRef, NexusConfig
from app.serialize import DEFAULT_SERIALIZER, SERIALIZERS_REGEX
from app.utils import attributes_to_dict, modality_to_attributes


class RegexParamType(click.ParamType):
    """ParamType for regular expressions."""

    name = "regex"

    def __init__(self, regex):
        """Initialize the object.

        Args:
            regex: regular expression.
        """
        self._regex = re.compile(regex)

    def convert(self, value, param, ctx):
        """Return the value if it matches the regular expression."""
        if not isinstance(value, str) or not self._regex.match(value):
            self.fail(f"{value!r} does not match regex {self._regex.pattern!r}", param, ctx)
        return value


@click.group()
def cli():
    """CLI tools."""


@cli.command()
@click.option("--circuit-id", help="Nexus circuit id")
@click.option("--input-path", type=click.Path(path_type=Path, exists=True))
@click.option("--output-path", type=click.Path(path_type=Path), required=True)
@click.option("--population-name")
@click.option("--sampling-ratio", type=float, default=0.01, show_default=True)
@click.option("--modality", multiple=True, type=RegexParamType(MODALITIES_REGEX))
@click.option("--region", multiple=True)
@click.option("--mtype", multiple=True)
@click.option("--node-set", default=None)
@click.option("--seed", type=int, default=0, show_default=True)
@click.option(
    "--how", type=RegexParamType(SERIALIZERS_REGEX), default=DEFAULT_SERIALIZER, show_default=True
)
def export(  # pylint: disable=too-many-arguments,too-many-locals
    circuit_id: str,
    input_path: Path,
    output_path: Path,
    population_name: str | None,
    sampling_ratio: float,
    modality: list[str] | None,
    region: list[str] | None,
    mtype: list[str] | None,
    node_set: str | None,
    seed: int,
    how: str,
) -> None:
    """Export circuit information to file."""
    L.info("Starting export")
    circuit_ref = CircuitRef(id=circuit_id, path=input_path)
    nexus_config = NexusConfig(token=os.getenv("NEXUS_TOKEN"))
    attributes = modality_to_attributes(modality)
    query = attributes_to_dict(region=region, mtype=mtype)
    queries = [query] if query else None
    jobs.read_circuit_job(
        nexus_config=nexus_config,
        circuit_ref=circuit_ref,
        population_name=population_name,
        sampling_ratio=sampling_ratio,
        attributes=attributes,
        queries=queries,
        node_set=node_set,
        seed=seed,
        how=how,
        use_cache=False,
        output_path=Path(output_path),
    )
    L.info("Done")


@cli.command()
@click.option("--circuit-id", help="Nexus circuit id")
@click.option("--input-path", type=click.Path(path_type=Path, exists=True))
@click.option("--output-path", type=click.Path(path_type=Path), required=True)
@click.option("--population-name", help="Node population name", required=True)
@click.option("--sampling-ratio", type=float, default=0.01, show_default=True)
@click.option("--seed", type=int, default=0, show_default=True)
def sample(
    circuit_id: str,
    input_path: Path,
    output_path: Path,
    population_name: str,
    sampling_ratio: float,
    seed: int,
) -> None:
    """Sample a node file."""
    L.info("Starting sampling")
    circuit_ref = CircuitRef(id=circuit_id, path=input_path)
    nexus_config = NexusConfig(token=os.getenv("NEXUS_TOKEN"))
    jobs.sample_job(
        nexus_config=nexus_config,
        circuit_ref=circuit_ref,
        output_path=Path(output_path),
        population_name=population_name,
        sampling_ratio=sampling_ratio,
        seed=seed,
    )
    L.info("Done")


if __name__ == "__main__":
    configure_logging()
    cli()  # pylint: disable=no-value-for-parameter
