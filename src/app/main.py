"""API entry points."""
import shutil
import tempfile
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from app import cache, serialize, service, utils
from app.constants import COMMIT_SHA, DEBUG, ORIGINS, PROJECT_PATH
from app.logger import L
from app.schemas import CountParams, DownsampleParams, NodeSetsParams, QueryParams, ValidatedQuery
from app.serialize import get_content_type, get_extension

app = FastAPI(debug=DEBUG)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "project": PROJECT_PATH,
        "status": "OK",
    }


@app.get("/version")
async def version() -> dict:
    """Version endpoint."""
    return {
        "project": PROJECT_PATH,
        "commit_sha": COMMIT_SHA,
    }


@app.get("/circuit")
async def read_circuit(
    params: Annotated[QueryParams, Depends(ValidatedQuery(QueryParams.from_simplified_params))]
) -> FileResponse:
    """Return information about a circuit, for backward compatibility."""
    return await query(params)


@app.post("/circuit/query")
async def query(params: QueryParams) -> FileResponse:
    """Return information about a circuit."""

    def cleanup() -> None:
        L.info("Removing temporary directory %s in background task", tmp_dir)
        shutil.rmtree(tmp_dir)

    content_type = get_content_type(params.how)
    extension = get_extension(params.how)
    tmp_dir = Path(tempfile.mkdtemp(prefix="output_"))
    output_path = tmp_dir / f"output.{extension}"
    await utils.run_process_executor(
        func=read_circuit_job,
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


@app.get("/circuit/downsample")
async def downsample(
    params: Annotated[DownsampleParams, Depends(ValidatedQuery(DownsampleParams))]
) -> FileResponse:
    """Downsample a node file."""

    def cleanup() -> None:
        L.info("Removing temporary directory %s", tmp_dir)
        shutil.rmtree(tmp_dir)

    tmp_dir = Path(tempfile.mkdtemp(prefix="output_"))
    output_path = tmp_dir / f"downsampled.{int(1 / params.sampling_ratio)}.h5"
    await utils.run_process_executor(
        func=downsample_job,
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
def count(params: Annotated[CountParams, Depends(ValidatedQuery(CountParams))]) -> dict:
    """Return the number of nodes in a circuit."""
    # not cpu intensive, it can run in the current thread
    return service.count(input_path=params.input_path, population_names=params.population_name)


@app.get("/circuit/node_sets")
def node_sets(params: Annotated[NodeSetsParams, Depends(ValidatedQuery(NodeSetsParams))]) -> dict:
    """Return the sorted list of node_sets in a circuit."""
    # not cpu intensive, it can run in the current thread
    return service.get_node_set_names(input_path=params.input_path)


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
