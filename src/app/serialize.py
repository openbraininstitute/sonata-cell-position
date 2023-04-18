"""Serialization functions."""
import tempfile
from collections.abc import Callable, Iterable, Iterator
from pathlib import Path
from typing import Any, TypedDict

import pandas as pd
import pyarrow as pa
from pyarrow import fs

from app.constants import MODALITIES
from app.logger import L
from app.utils import modality_names_to_columns


def _data_generator_parquet(
    modality_names: list[str], df: pd.DataFrame, tmp_dir: Path
) -> Iterator[dict[str, Any]]:
    for modality_name in modality_names:
        wanted = MODALITIES[modality_name]
        tmp_file = tmp_dir / f"{modality_name}.tmp"
        df[wanted].to_parquet(tmp_file, engine="pyarrow", index=False)
        yield (
            {
                "dataset_name": modality_name,
                "filepath": str(tmp_file.resolve()),
                "metadata": {"type": "CellRecordSeries"},
            }
        )


def _data_generator_rab(
    modality_names: list[str], df: pd.DataFrame, tmp_dir: Path
) -> Iterator[dict[str, Any]]:
    # pylint: disable=unused-argument
    for modality_name in modality_names:
        wanted = MODALITIES[modality_name]
        yield (
            {
                "dataset_name": modality_name,
                "data": df[wanted],
                "compress": "gzip",
                "metadata": {"type": "CellRecordSeries"},
            }
        )


def _write_rab(filename: Path, data: Iterable[dict[str, Any]]) -> None:
    import randomaccessbuffer as rab  # pylint: disable=import-error,import-outside-toplevel

    rab_instance = rab.RandomAccessBuffer()
    for d in data:
        L.info("Generating and adding dataset %s to RAB file", d.get("dataset_name"))
        rab_instance.addDataset(**d)
    L.info("Writing RAB file")
    rab_instance.write(filename)


def to_rab(
    df: pd.DataFrame, modality_names: list[str], output_path: Path, attrs: str | None
) -> None:
    """Write a DataFrame to file in RAB format."""
    generator = {
        "parquet": _data_generator_parquet,
        "rab": _data_generator_rab,
    }[attrs or "parquet"]
    with tempfile.TemporaryDirectory() as tmp_dir:
        iterator = generator(modality_names, df, tmp_dir=Path(tmp_dir))
        _write_rab(filename=output_path, data=iterator)


def to_parquet(
    df: pd.DataFrame, modality_names: list[str], output_path: Path, attrs: str | None
) -> None:
    """Write a DataFrame to file in parquet format."""
    # pylint: disable=unused-argument
    columns = modality_names_to_columns(modality_names)
    df[columns].to_parquet(output_path, engine="pyarrow", index=False)


def to_json(
    df: pd.DataFrame, modality_names: list[str], output_path: Path, attrs: str | None
) -> None:
    """Write a DataFrame to file in JSON format."""
    columns = modality_names_to_columns(modality_names)
    orient = attrs or "columns"
    df[columns].to_json(output_path, orient=orient)


def to_arrow(
    df: pd.DataFrame, modality_names: list[str], output_path: Path, attrs: str | None
) -> None:
    """Write a DataFrame to file in arrow format."""
    # pylint: disable=unused-argument
    columns = modality_names_to_columns(modality_names)
    table = pa.Table.from_pandas(df[columns])
    with fs.LocalFileSystem().open_output_stream(str(output_path)) as file:
        with pa.RecordBatchFileWriter(file, table.schema) as writer:
            writer.write_table(table)


def write(df: pd.DataFrame, modality_names: list[str] | None, output_path: Path, how: str) -> None:
    """Write a DataFrame to file."""
    how, _, attrs = how.partition(":")
    serializer = SERIALIZERS[how]["function"]
    modality_names = modality_names or list(MODALITIES)
    serializer(df, modality_names, output_path, attrs)


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
    "rab": {
        "function": to_rab,
        # prs: non publicly available products or experimental media types
        "content_type": "application/prs.rab",
        "extension": "rab",
    },
}
SERIALIZERS_REGEX = f"^({'|'.join(SERIALIZERS)})(:.*)?$"
DEFAULT_SERIALIZER = "rab:parquet"
