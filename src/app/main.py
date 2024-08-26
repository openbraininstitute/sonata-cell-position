"""API entry points."""

import os
import tempfile
from collections.abc import Callable, Iterator
from contextlib import asynccontextmanager
from http.client import responses
from pathlib import Path
from typing import Annotated

from fastapi import BackgroundTasks, Depends, FastAPI, Query
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, RedirectResponse, Response
from starlette.status import HTTP_302_FOUND

from app import jobs, nexus, serialize, service, utils
from app.config import settings
from app.errors import ClientError
from app.logger import L
from app.schemas import CircuitRef, NexusConfig, QueryParams, SampleParams

# dependency aliases
NexusConfigDep = Annotated[NexusConfig, Depends(NexusConfig.from_headers)]
CircuitRefDep = Annotated[CircuitRef, Depends(CircuitRef.from_params)]


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Execute actions on server startup and shutdown."""
    L.info(
        "Starting application [PID={}, CPU_COUNT={}]",
        os.getpid(),
        os.cpu_count(),
    )
    service.get_bundled_region_map()
    utils.warmup_executors()
    yield
    L.info("Stopping the application")


app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.APP_DEBUG,
    lifespan=lifespan,
    root_path=settings.ROOT_PATH,
)


def no_cache(response: Response) -> Response:
    """Add Cache-Control: no-cache to the response headers.

    It can be used as a dependency in any endpoint. Usage example:

        @app.get("/health", dependencies=[Depends(no_cache)])
        async def health() -> dict:
        ...

    """
    response.headers["Cache-Control"] = "no-cache"
    return response


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


@app.exception_handler(ClientError)
async def client_error_handler(request: Request, exc: ClientError) -> JSONResponse:
    """Handle application errors to be returned to the client."""
    # pylint: disable=unused-argument
    msg = f"{exc.__class__.__name__}: {exc}"
    L.warning(msg)
    return JSONResponse(status_code=exc.status_code, content={"message": msg})


@app.get("/")
async def root():
    """Root endpoint."""
    return RedirectResponse(url=f"{settings.ROOT_PATH}/docs", status_code=HTTP_302_FOUND)


@app.get("/health", dependencies=[Depends(no_cache)])
async def health() -> dict:
    """Health endpoint."""
    return {
        "status": "OK",
    }


@app.get("/version", dependencies=[Depends(no_cache)])
async def version() -> dict:
    """Version endpoint."""
    return {
        "app_name": settings.APP_NAME,
        "app_version": settings.APP_VERSION,
        "commit_sha": settings.COMMIT_SHA,
    }


@app.get("/auth", include_in_schema=False)
def auth(
    nexus_config: NexusConfigDep,
) -> JSONResponse:
    """Auth endpoint."""
    status_code = nexus.is_user_authorized(nexus_config)
    return JSONResponse(
        content={"message": responses[status_code]},
        status_code=status_code,
    )


@app.get("/circuit")
def read_circuit(
    nexus_config: NexusConfigDep,
    params: Annotated[QueryParams, Depends(QueryParams.from_simplified_params)],
    tmp_path: Annotated[Path, Depends(make_temp_path(prefix="output_"))],
) -> FileResponse:
    """Return information about a circuit (cacheable)."""
    return query(nexus_config=nexus_config, params=params, tmp_path=tmp_path)


@app.post("/circuit/query")
def query(
    nexus_config: NexusConfigDep,
    params: QueryParams,
    tmp_path: Annotated[Path, Depends(make_temp_path(prefix="output_"))],
) -> FileResponse:
    """Return information about a circuit."""
    circuit_ref = CircuitRef.from_params(circuit_id=params.circuit_id)
    content_type = serialize.get_content_type(params.how)
    extension = serialize.get_extension(params.how)
    output_path = tmp_path / f"output.{extension}"
    jobs.read_circuit_job(
        nexus_config=nexus_config,
        circuit_ref=circuit_ref,
        population_name=params.population_name,
        sampling_ratio=params.sampling_ratio,
        attributes=params.attributes,
        queries=params.queries,
        node_set=params.node_set,
        seed=params.seed,
        how=params.how,
        use_cache=params.use_cache,
        output_path=output_path,
    )
    return FileResponse(
        output_path,
        media_type=content_type,
        filename=output_path.name,
    )


@app.post("/circuit/sample")
def sample(
    nexus_config: NexusConfigDep,
    params: SampleParams,
    tmp_path: Annotated[Path, Depends(make_temp_path(prefix="output_"))],
) -> FileResponse:
    """Sample a node file."""
    circuit_ref = CircuitRef.from_params(circuit_id=params.circuit_id)
    output_path = tmp_path / f"sampled_{params.sampling_ratio}.h5"
    jobs.sample_job(
        nexus_config=nexus_config,
        circuit_ref=circuit_ref,
        output_path=output_path,
        population_name=params.population_name,
        sampling_ratio=params.sampling_ratio,
        seed=params.seed,
    )
    return FileResponse(
        output_path,
        media_type="application/octet-stream",
        filename=output_path.name,
    )


@app.get("/circuit/count")
def count(
    nexus_config: NexusConfigDep,
    circuit_ref: CircuitRefDep,
    population_name: str | None = None,
) -> dict:
    """Return the number of nodes in a circuit."""
    path = service.get_circuit_config_path(circuit_ref, nexus_config=nexus_config)
    return service.count(input_path=path, population_name=population_name)


@app.get("/circuit/attribute_names")
def get_attribute_names(
    nexus_config: NexusConfigDep,
    circuit_ref: CircuitRefDep,
    population_name: str | None = None,
) -> dict:
    """Return the attribute names of a circuit."""
    path = service.get_circuit_config_path(circuit_ref, nexus_config=nexus_config)
    return service.get_attribute_names(input_path=path, population_name=population_name)


@app.get("/circuit/attribute_dtypes")
def get_attribute_dtypes(
    nexus_config: NexusConfigDep,
    circuit_ref: CircuitRefDep,
    population_name: str | None = None,
) -> dict:
    """Return the attribute data types of a circuit."""
    path = service.get_circuit_config_path(circuit_ref, nexus_config=nexus_config)
    return service.get_attribute_dtypes(input_path=path, population_name=population_name)


@app.get("/circuit/attribute_values")
def get_attribute_values(
    nexus_config: NexusConfigDep,
    circuit_ref: CircuitRefDep,
    population_name: str | None = None,
    attribute_names: Annotated[list[str] | None, Query()] = None,
) -> dict:
    """Return the unique values of the attributes of a circuit."""
    path = service.get_circuit_config_path(circuit_ref, nexus_config=nexus_config)
    return service.get_attribute_values(
        input_path=path,
        population_name=population_name,
        attribute_names=attribute_names,
    )


@app.get("/circuit/node_sets")
def node_sets(
    nexus_config: NexusConfigDep,
    circuit_ref: CircuitRefDep,
) -> dict:
    """Return the sorted list of node_sets in a circuit."""
    path = service.get_circuit_config_path(circuit_ref, nexus_config=nexus_config)
    return service.get_node_set_names(input_path=path)
