"""Common utilities."""

import functools
import json
import os
import time
from collections.abc import Callable
from itertools import chain
from pathlib import Path
from typing import Any

import pandas as pd
from loky import get_reusable_executor
from loky.backend.context import set_start_method

from app.config import settings
from app.constants import MODALITIES
from app.logger import L


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


def with_pid(func: Callable) -> Callable:
    """Decorator used to run a function and log pid and elapsed time."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        """Execute a function and return a tuple (result, pid)."""
        start_time = time.monotonic()
        pid = os.getpid()
        try:
            return func(*args, **kwargs)
        finally:
            exec_time = time.monotonic() - start_time
            L.info("Executed %s in process %s in %.3f seconds", func.__name__, pid, exec_time)

    return wrapper


def prepare_callable(func: Callable, *args, **kwargs) -> Callable[[], Any]:
    """Return a callable that can be called without arguments to get the result."""
    executor = get_reusable_executor(
        max_workers=settings.LOKY_EXECUTOR_MAX_WORKERS,
        timeout=settings.LOKY_EXECUTOR_TIMEOUT,
    )
    future = executor.submit(func, *args, **kwargs)
    return future.result


def warmup_executors() -> None:
    """Warm up the executors."""
    if settings.LOKY_EXECUTOR_ENABLED:

        def _import_all():
            # pylint: disable=import-outside-toplevel,unused-import,cyclic-import
            from app import main  # noqa

        L.info("Warming up subprocess executors")
        set_start_method(settings.LOKY_START_METHOD)
        wrapped_func = with_pid(_import_all)
        # submit a callable to each worker, without blocking
        func_list = [
            prepare_callable(wrapped_func) for i in range(settings.LOKY_EXECUTOR_MAX_WORKERS)
        ]
        # block until all the results are ready
        for func in func_list:
            func()


def run_subprocess(func: Callable) -> Callable:
    """Decorator used to run a function in a subprocess.

    To avoid creating a new process each time, the process is executed using a persistent pool.

    This can be useful when the function is I/O bound, and it doesn't release the GIL,
    for example when calling libsonata functions doing heavy I/O operations.

    It can be useful also when the function is CPU bound, provided that there are available cores.

    Be aware that there may be some overhead to serialize and deserialize parameters and result.

    If LOKY_EXECUTOR_ENABLED is False, then the function is executed in the current process.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        """Execute the wrapped function."""
        wrapped_func = with_pid(func)
        if settings.LOKY_EXECUTOR_ENABLED:
            return prepare_callable(wrapped_func, *args, **kwargs)()
        else:
            return wrapped_func(*args, **kwargs)

    return wrapper
