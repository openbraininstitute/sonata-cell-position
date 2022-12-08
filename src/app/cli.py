"""CLI entry point."""
import re
from pathlib import Path
from typing import List, Optional

import click

import app.main
from app.logger import L
from app.serialize import DEFAULT_SERIALIZER, SERIALIZERS_REGEX


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


@click.command()
@click.option("--input-path", type=click.Path(exists=True), required=True)
@click.option("--output-path", type=click.Path(), required=True)
@click.option("--population-name")
@click.option("--sampling-ratio", type=float, default=0.01, show_default=True)
@click.option("--modality", multiple=True)
@click.option("--region", multiple=True)
@click.option("--mtype", multiple=True)
@click.option("--seed", type=int, default=0, show_default=True)
@click.option(
    "--how", type=RegexParamType(SERIALIZERS_REGEX), default=DEFAULT_SERIALIZER, show_default=True
)
def main(
    input_path: str,
    output_path: str,
    population_name: Optional[str],
    sampling_ratio: float,
    modality: Optional[List[str]],
    region: Optional[List[str]],
    mtype: Optional[List[str]],
    seed: int,
    how: str,
) -> None:
    """Export circuit information to file."""
    L.info("Starting export")
    app.main.read_circuit_job(
        input_path=Path(input_path),
        population_name=population_name,
        sampling_ratio=sampling_ratio,
        modality_names=modality,
        regions=region,
        mtypes=mtype,
        seed=seed,
        how=how,
        output_path=Path(output_path),
    )
    L.info("Done")


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
