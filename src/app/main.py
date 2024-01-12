"""API entry points."""
import shutil
import tempfile
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from starlette.background import BackgroundTask
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, RedirectResponse, Response
from starlette.status import HTTP_302_FOUND, HTTP_400_BAD_REQUEST

from app import cache, serialize, service
from app.constants import COMMIT_SHA, DEBUG, ORIGINS, PROJECT_PATH
from app.errors import CircuitError
from app.logger import L
from app.schemas import CircuitConfigPath, DownsampleParams, QueryParams, ValidatedQuery
from app.serialize import get_content_type, get_extension

app = FastAPI(debug=DEBUG)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def no_cache(response: Response) -> Response:
    """Add Cache-Control: no-cache to the response headers."""
    response.headers["Cache-Control"] = "no-cache"
    return response


@app.exception_handler(CircuitError)
async def circuit_error_handler(request: Request, exc: CircuitError) -> JSONResponse:
    """Handle CircuitError."""
    # pylint: disable=unused-argument
    msg = f"CircuitError: {exc}"
    L.warning(msg)
    return JSONResponse(status_code=HTTP_400_BAD_REQUEST, content={"message": msg})


@app.get("/")
async def root():
    """Root endpoint."""
    return RedirectResponse(url="/docs", status_code=HTTP_302_FOUND)


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
        "project": PROJECT_PATH,
        "commit_sha": COMMIT_SHA,
    }


@app.get("/circuit")
def read_circuit(
    params: Annotated[QueryParams, Depends(ValidatedQuery(QueryParams.from_simplified_params))]
) -> FileResponse:
    """Return information about a circuit, for backward compatibility."""
    return query(params)


@app.post("/circuit/query")
def query(params: QueryParams) -> FileResponse:
    """Return information about a circuit."""

    def cleanup() -> None:
        L.info("Removing temporary directory %s in background task", tmp_dir)
        shutil.rmtree(tmp_dir)

    content_type = get_content_type(params.how)
    extension = get_extension(params.how)
    tmp_dir = Path(tempfile.mkdtemp(prefix="output_"))
    output_path = tmp_dir / f"output.{extension}"
    read_circuit_job(
        input_path=params.input_path,
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
        background=BackgroundTask(cleanup),
    )


@app.post("/circuit/downsample")
def downsample(params: DownsampleParams) -> FileResponse:
    """Downsample a node file."""

    def cleanup() -> None:
        L.info("Removing temporary directory %s", tmp_dir)
        shutil.rmtree(tmp_dir)

    tmp_dir = Path(tempfile.mkdtemp(prefix="output_"))
    output_path = tmp_dir / f"downsampled.{int(1 / params.sampling_ratio)}.h5"
    downsample_job(
        input_path=params.input_path,
        output_path=output_path,
        population_name=params.population_name,
        sampling_ratio=params.sampling_ratio,
        seed=params.seed,
    )
    return FileResponse(
        output_path,
        media_type="application/octet-stream",
        filename=output_path.name,
        background=BackgroundTask(cleanup),
    )


@app.get("/circuit/count")
def count(
    input_path: CircuitConfigPath,
    population_name: str | None = None,
) -> dict:
    """Return the number of nodes in a circuit."""
    # not cpu intensive, it can run in the current thread
    return service.count(input_path=input_path, population_name=population_name)


@app.get("/circuit/attribute_names")
def get_attribute_names(
    input_path: CircuitConfigPath,
    population_name: str | None = None,
) -> dict:
    """Return the attribute names of a circuit."""
    return service.get_attribute_names(input_path=input_path, population_name=population_name)


@app.get("/circuit/attribute_dtypes")
def get_attribute_dtypes(
    input_path: CircuitConfigPath,
    population_name: str | None = None,
) -> dict:
    """Return the attribute data types of a circuit."""
    return service.get_attribute_dtypes(input_path=input_path, population_name=population_name)


@app.get("/circuit/attribute_values")
def get_attribute_values(
    input_path: CircuitConfigPath,
    population_name: str | None = None,
    attribute_names: Annotated[list[str] | None, Query()] = None,
) -> dict:
    """Return the unique values of the attributes of a circuit."""
    return service.get_attribute_values(
        input_path=input_path,
        population_name=population_name,
        attribute_names=attribute_names,
    )


@app.get("/circuit/node_sets")
def node_sets(input_path: CircuitConfigPath) -> dict:
    """Return the sorted list of node_sets in a circuit."""
    # not cpu intensive, it can run in the current thread
    return service.get_node_set_names(input_path=input_path)


def read_circuit_job(
    input_path: Path,
    population_name: str | None,
    sampling_ratio: float,
    attributes: list[str],
    queries: list[dict[str, Any]] | None,
    node_set: str | None,
    seed: int,
    how: str,
    use_cache: bool,
    output_path: Path,
) -> None:
    """Function that can be pickled and executed in a subprocess."""
    # pylint: disable=too-many-arguments
    cache_params = cache.CacheParams(
        input_path=input_path,
        population_name=population_name,
        attributes=attributes,
        sampling_ratio=sampling_ratio,
        seed=seed,
    )
    if use_cache:
        cache_params = cache.check_cache(cache_params)
    df = service.export(
        input_path=cache_params.input_path,
        population_name=cache_params.population_name,
        sampling_ratio=cache_params.sampling_ratio,
        queries=queries,
        attributes=attributes,
        node_set=node_set,
        seed=cache_params.seed,
    )
    serialize.write(df=df, attributes=attributes, output_path=output_path, how=how)


def downsample_job(
    input_path: Path,
    output_path: Path,
    population_name: str | None,
    sampling_ratio: float,
    seed: int,
) -> None:
    """Function that can be pickled and executed in a subprocess."""
    service.downsample(
        input_path=input_path,
        output_path=output_path,
        population_name=population_name,
        sampling_ratio=sampling_ratio,
        seed=seed,
    )
