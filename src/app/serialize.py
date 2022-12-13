"""Serialization functions."""
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional

import pandas as pd
import pyarrow as pa
import randomaccessbuffer as rab  # pylint: disable=import-error
from pyarrow import fs

from app.constants import MODALITIES
from app.logger import L
from app.utils import modality_names_to_columns


def _data_generator_parquet(
    modality_names: List[str], df: pd.DataFrame, tmp_dir: Path
) -> Iterator[Dict[str, Any]]:
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
    modality_names: List[str], df: pd.DataFrame, tmp_dir: Path
) -> Iterator[Dict[str, Any]]:
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


def _write_rab(filename: Path, data: Iterable[Dict[str, Any]]) -> None:
    rab_instance = rab.RandomAccessBuffer()
    for d in data:
        L.info("Generating and adding dataset %s to RAB file", d.get("dataset_name"))
        rab_instance.addDataset(**d)
    L.info("Writing RAB file")
    rab_instance.write(filename)


def to_rab(
    df: pd.DataFrame, modality_names: List[str], output_path: Path, attrs: Optional[str]
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
    df: pd.DataFrame, modality_names: List[str], output_path: Path, attrs: Optional[str]
) -> None:
    """Write a DataFrame to file in parquet format."""
    # pylint: disable=unused-argument
    columns = modality_names_to_columns(modality_names)
    df[columns].to_parquet(output_path, engine="pyarrow", index=False)


def to_json(
    df: pd.DataFrame, modality_names: List[str], output_path: Path, attrs: Optional[str]
) -> None:
    """Write a DataFrame to file in JSON format."""
    columns = modality_names_to_columns(modality_names)
    orient = attrs or "columns"
    df[columns].to_json(output_path, orient=orient)


def to_arrow(
    df: pd.DataFrame, modality_names: List[str], output_path: Path, attrs: Optional[str]
) -> None:
    """Write a DataFrame to file in arrow format."""
    # pylint: disable=unused-argument
    columns = modality_names_to_columns(modality_names)
    table = pa.Table.from_pandas(df[columns])
    with fs.LocalFileSystem().open_output_stream(str(output_path)) as file:
        with pa.RecordBatchFileWriter(file, table.schema) as writer:
            writer.write_table(table)


def write(
    df: pd.DataFrame, modality_names: Optional[List[str]], output_path: Path, how: str
) -> None:
    """Write a DataFrame to file."""
    how, _, attrs = how.partition(":")
    serializer = SERIALIZERS[how]
    modality_names = modality_names or list(MODALITIES)
    return serializer(df, modality_names, output_path, attrs)


SERIALIZERS = {
    "arrow": to_arrow,
    "json": to_json,
    "parquet": to_parquet,
    "rab": to_rab,
}
SERIALIZERS_REGEX = f"^({'|'.join(SERIALIZERS)})(:.*)?$"
DEFAULT_SERIALIZER = "rab:parquet"
