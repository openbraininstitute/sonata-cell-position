"""Common utilities."""
import asyncio
import concurrent.futures
from functools import partial
from itertools import chain
from typing import Any, List

from app.constants import MODALITIES


def ensure_list(x: Any) -> List[Any]:
    """Return x if x is already a list, [x] otherwise."""
    return x if isinstance(x, list) else [x]


def modality_names_to_columns(modality_names: List[str]) -> List[str]:
    """Convert a list of modality names to columns."""
    return list(chain.from_iterable(MODALITIES[modality] for modality in modality_names))


async def run_process_executor(func, **params):
    """Run a cpu-intensive function in a subprocess."""
    loop = asyncio.get_running_loop()
    func = partial(func, **params)
    with concurrent.futures.ProcessPoolExecutor() as pool:
        await loop.run_in_executor(pool, func)
