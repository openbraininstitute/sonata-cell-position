"""Common utilities."""

import json
import os
from itertools import chain
from pathlib import Path
from typing import Any

import pandas as pd

from app.constants import MODALITIES


def dump_json(
    filepath: Path | str, data: Any, *, encoding: str = "utf-8", indent: int = 2, **kwargs
) -> None:
    """Dump an object to JSON file."""
    with open(filepath, mode="w", encoding=encoding) as fp:
        json.dump(data, fp, indent=indent, **kwargs)


def load_json(filepath: Path | str, *, encoding: str = "utf-8", **kwargs) -> Any:
    """Load an object from JSON file."""
    with open(filepath, encoding=encoding) as fp:
        return json.load(fp, **kwargs)


def ensure_list(x: Any) -> list[Any]:
    """Return x if x is already a list, [x] otherwise."""
    return list(x) if isinstance(x, list | tuple) else [x]


def ensure_dtypes(df: pd.DataFrame, dtypes: dict[str, Any]) -> pd.DataFrame:
    """Return a copy of the DataFrame with the desired dtypes depending on the column names.

    If no conversions are needed, return the original DataFrame.
    """
    dtypes = {k: dtypes[k] for k in df.columns if k in dtypes and dtypes[k] != df.dtypes.at[k]}
    if not dtypes:
        return df
    return df.astype(dtypes)


def modality_to_attributes(modality: list[str] | None = None) -> list[str]:
    """Convert a list of modality names to attributes."""
    modality = modality or list(MODALITIES)
    return list(chain.from_iterable(MODALITIES[modality] for modality in modality))


def attributes_to_dict(**kwargs) -> dict[str, Any]:
    """Convert attributes to dict, filtering out empty values."""
    return {key: value for key, value in kwargs.items() if value}


def get_folder_size(path: Path | str) -> int:
    """Return the size of the given directory in bytes, without following symlinks."""
    total = os.stat(path, follow_symlinks=False).st_size
    with os.scandir(path) as it:
        for entry in it:
            if entry.is_dir():
                total += get_folder_size(entry.path)
            else:
                total += entry.stat(follow_symlinks=False).st_size
    return total
