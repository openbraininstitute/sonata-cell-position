"""Serialization functions."""
from collections.abc import Callable
from pathlib import Path
from typing import TypedDict

import pandas as pd
import pyarrow as pa
from pyarrow import fs


def to_parquet(
    df: pd.DataFrame, attributes: list[str], output_path: Path, attrs: str | None
) -> None:
    """Write a DataFrame to file in parquet format."""
    # pylint: disable=unused-argument
    df[attributes].to_parquet(output_path, engine="pyarrow", index=False)


def to_json(df: pd.DataFrame, attributes: list[str], output_path: Path, attrs: str | None) -> None:
    """Write a DataFrame to file in JSON format."""
    orient = attrs or "columns"
    df[attributes].to_json(output_path, orient=orient)


def to_arrow(df: pd.DataFrame, attributes: list[str], output_path: Path, attrs: str | None) -> None:
    """Write a DataFrame to file in arrow format."""
    # pylint: disable=unused-argument
    table = pa.Table.from_pandas(df[attributes])
    with fs.LocalFileSystem().open_output_stream(str(output_path)) as file:
        with pa.RecordBatchFileWriter(file, table.schema) as writer:
            writer.write_table(table)


def write(df: pd.DataFrame, attributes: list[str], output_path: Path, how: str) -> None:
    """Write a DataFrame to file."""
    how, _, attrs = how.partition(":")
    serializer = SERIALIZERS[how]["function"]
    serializer(df, attributes, output_path, attrs)


def get_content_type(how: str) -> str:
    """Return the content-type corresponding to the given type."""
    how = how.partition(":")[0]
    return SERIALIZERS[how]["content_type"]


def get_extension(how: str) -> str:
    """Return the extension corresponding to the given type."""
    how = how.partition(":")[0]
    return SERIALIZERS[how]["extension"]


class Serializer(TypedDict):
    """Serializer type."""

    function: Callable[[pd.DataFrame, list[str], Path, str | None], None]
    content_type: str
    extension: str


SERIALIZERS: dict[str, Serializer] = {
    "arrow": {
        "function": to_arrow,
        "content_type": "application/vnd.apache.arrow.file",
        "extension": "arrow",
    },
    "json": {
        "function": to_json,
        "content_type": "application/json",
        "extension": "json",
    },
    "parquet": {
        "function": to_parquet,
        # not registered yet, see https://issues.apache.org/jira/browse/PARQUET-1889
        "content_type": "application/vnd.apache.parquet",
        "extension": "parquet",
    },
}
SERIALIZERS_REGEX = f"^({'|'.join(SERIALIZERS)})(:.*)?$"
DEFAULT_SERIALIZER = "arrow"
