"""FastAPI dependencies."""

import tempfile
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Annotated

from fastapi import BackgroundTasks, Depends
from starlette.requests import Request
from starlette.responses import Response

from app.logger import L
from app.schemas import CircuitRef, NexusConfig


def make_temp_path(suffix=None, prefix=None) -> Callable:
    """Return a function that creates a temporary directory and remove it at the end.

    It can be used as a dependency in any endpoint. Usage example:

        @app.get("/circuit")
        def read_circuit(tmp_path: Annotated[Path, Depends(make_temp_path(prefix="output_"))]):
        ...

    """

    def func(background_tasks: BackgroundTasks) -> Iterator[Path]:
        """Create a temporary directory and remove it at the end."""

        def cleanup():
            L.info("Removing directory {}", temp_dir.name)
            temp_dir.cleanup()

        # pylint: disable=consider-using-with
        temp_dir = tempfile.TemporaryDirectory(suffix=suffix, prefix=prefix)
        background_tasks.add_task(cleanup)
        try:
            yield Path(temp_dir.name)
        except BaseException:
            # remove the directory in case of unhandled exception
            cleanup()
            raise

    return func


# dependency aliases
NexusConfigDep = Annotated[NexusConfig, Depends(NexusConfig.from_headers)]
CircuitRefDep = Annotated[CircuitRef, Depends(CircuitRef.from_params)]


class CacheControl:
    """Add Cache-Control to the response headers.

    It can be used as a dependency in any endpoint. Usage example:

        @app.get("/health", dependencies=[Depends(CacheControl("no-cache"))])
        async def health() -> dict:
        ...

    """

    def __init__(self, *values: str) -> None:
        """Init the instance with a list of values."""
        self._values = values

    def __call__(self, request: Request, response: Response) -> Response:
        """Add the header."""
        if request.method == "GET":
            response.headers["Cache-Control"] = ", ".join(self._values)
        return response


no_cache = CacheControl("no-cache")
