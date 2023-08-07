"""Common utilities."""
import asyncio
import concurrent.futures
from functools import partial
from itertools import chain
from typing import Any

import pandas as pd

from app.constants import MODALITIES


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


async def run_process_executor(func, **params):
    """Run a cpu-intensive function in a subprocess."""
    loop = asyncio.get_running_loop()
    func = partial(func, **params)
    with concurrent.futures.ProcessPoolExecutor() as pool:
        await loop.run_in_executor(pool, func)
