"""Common utilities."""
import asyncio
import concurrent.futures
from functools import partial
from itertools import chain
from typing import Any, List, Optional

from app.constants import MODALITIES


def ensure_list(x: Any) -> List[Any]:
    """Return x if x is already a list, [x] otherwise."""
    return list(x) if isinstance(x, (list, tuple)) else [x]


def modality_names_to_columns(modality_names: Optional[List[str]] = None) -> List[str]:
    """Convert a list of modality names to columns."""
    modality_names = modality_names or list(MODALITIES)
    return list(chain.from_iterable(MODALITIES[modality] for modality in modality_names))


async def run_process_executor(func, **params):
    """Run a cpu-intensive function in a subprocess."""
    loop = asyncio.get_running_loop()
    func = partial(func, **params)
    with concurrent.futures.ProcessPoolExecutor() as pool:
        await loop.run_in_executor(pool, func)
