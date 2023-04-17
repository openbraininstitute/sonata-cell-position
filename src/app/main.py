"""API entry points."""
import shutil
import tempfile
from collections.abc import Callable
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from app import cache, serialize, service, utils
from app.constants import COMMIT_SHA, DEBUG, ORIGINS, PROJECT_PATH
from app.logger import L
from app.serialize import DEFAULT_SERIALIZER, SERIALIZERS_REGEX, get_content_type, get_extension

app = FastAPI(debug=DEBUG)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _validate_path(extensions: set[str] | None = None) -> Callable[[Path], Path]:
    def validate(input_path: Path = Query(...)) -> Path:
        if extensions and input_path.suffix not in extensions:
            L.warning("Path forbidden: %s", input_path)
            raise HTTPException(status_code=403, detail="Path forbidden")
        if not input_path.exists():
            L.warning("Path not found: %s", input_path)
            raise HTTPException(status_code=404, detail="Path not found")
        return input_path

    return validate


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


@app.get("/circuit", response_class=FileResponse)
async def read_circuit(
    input_path: Path = Depends(_validate_path({"json", ".h5"})),
    region: list[str] | None = Query(default=None),
    mtype: list[str] | None = Query(default=None),
    modality: list[str] | None = Query(default=None),
    population_name: str | None = None,
    sampling_ratio: float = 0.01,
    seed: int = 0,
    how: str = Query(default=DEFAULT_SERIALIZER, regex=SERIALIZERS_REGEX),
    use_cache: bool = True,
) -> FileResponse:
    """Return information about a circuit."""

    def cleanup() -> None:
        L.info("Removing temporary directory %s in background task", tmp_dir)
        shutil.rmtree(tmp_dir)

    content_type = get_content_type(how)
    extension = get_extension(how)
    tmp_dir = Path(tempfile.mkdtemp(prefix="output_"))
    output_path = tmp_dir / f"output.{extension}"
    await utils.run_process_executor(
        func=read_circuit_job,
        input_path=input_path,
        population_name=population_name,
        sampling_ratio=sampling_ratio,
        modality_names=modality,
        regions=region,
        mtypes=mtype,
        seed=seed,
        how=how,
        use_cache=use_cache,
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
    input_path: Path = Depends(_validate_path({".json", ".h5"})),
    population_name: str | None = None,
    sampling_ratio: float = 0.01,
    seed: int = 0,
) -> FileResponse:
    """Downsample a node file."""

    def cleanup() -> None:
        L.info("Removing temporary directory %s", tmp_dir)
        shutil.rmtree(tmp_dir)

    tmp_dir = Path(tempfile.mkdtemp(prefix="output_"))
    output_path = tmp_dir / f"downsampled.{int(1 / sampling_ratio)}.h5"
    await utils.run_process_executor(
        func=downsample_job,
        input_path=input_path,
        output_path=output_path,
        population_name=population_name,
        sampling_ratio=sampling_ratio,
        seed=seed,
    )
    return FileResponse(
        output_path,
        media_type="application/octet-stream",
        filename=output_path.name,
        background=BackgroundTask(cleanup),
    )


@app.get("/circuit/count")
def count(
    input_path: Path = Depends(_validate_path({".json", ".h5"})),
    population_name: list[str] | None = Query(default=None),
) -> dict:
    """Return the number of nodes in a circuit."""
    # not cpu intensive, it can run in the current thread
    return service.count(input_path=input_path, population_names=population_name)


@app.get("/circuit/node_sets")
def node_sets(input_path: Path = Depends(_validate_path({".json"}))) -> dict:
    """Return the sorted list of node_sets in a circuit."""
    # not cpu intensive, it can run in the current thread
    return service.get_node_sets(input_path=input_path)


def read_circuit_job(
    input_path: Path,
    population_name: str | None,
    sampling_ratio: float,
    modality_names: list[str] | None,
    regions: list[str] | None,
    mtypes: list[str] | None,
    seed: int,
    how: str,
    use_cache: bool,
    output_path: Path,
) -> None:
    """Function that can be pickled and executed in a subprocess."""
    # pylint: disable=too-many-arguments
    cache_params: cache.CacheParams = {
        "input_path": input_path,
        "population_name": population_name,
        "sampling_ratio": sampling_ratio,
        "seed": seed,
    }
    if use_cache:
        cache_params.update(cache.check_cache(**cache_params))
    df = service.export(
        modality_names=modality_names,
        regions=regions,
        mtypes=mtypes,
        **cache_params,
    )
    serialize.write(df=df, modality_names=modality_names, output_path=output_path, how=how)


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
