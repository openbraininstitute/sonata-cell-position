"""API entry points."""
import json
import shutil
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from app import serialize, service, utils
from app.constants import ALLOWED_EXTENSIONS, COMMIT_SHA, DEBUG, ORIGINS, PROJECT_PATH
from app.logger import L
from app.serialize import DEFAULT_SERIALIZER, SERIALIZERS_REGEX

app = FastAPI(debug=DEBUG)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _validate_path(input_path: Path = Query(...)) -> Path:
    if input_path.suffix not in ALLOWED_EXTENSIONS:
        L.warning("Path forbidden: %s", input_path)
        raise HTTPException(status_code=403, detail="Path forbidden")
    if not input_path.exists():
        L.warning("Path not found: %s", input_path)
        raise HTTPException(status_code=404, detail="Path not found")
    return input_path


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "project": PROJECT_PATH,
        "status": "OK",
    }


@app.get("/version")
async def version() -> Dict:
    """Version endpoint."""
    return {
        "project": PROJECT_PATH,
        "commit_sha": COMMIT_SHA,
    }


@app.get("/circuit", response_class=FileResponse)
async def read_circuit(
    input_path: Path = Depends(_validate_path),
    region: Optional[List[str]] = Query(default=None),
    mtype: Optional[List[str]] = Query(default=None),
    modality: Optional[List[str]] = Query(default=None),
    population_name: Optional[str] = None,
    sampling_ratio: float = 0.01,
    seed: int = 0,
    how: str = Query(default=DEFAULT_SERIALIZER, regex=SERIALIZERS_REGEX),
) -> FileResponse:
    """Return information about a circuit."""

    def cleanup() -> None:
        L.info("Removing temporary directory %s in background task", tmp_dir)
        shutil.rmtree(tmp_dir)

    tmp_dir = Path(tempfile.mkdtemp(prefix="output_"))
    output_path = tmp_dir / "output.bin"
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
        output_path=output_path,
    )
    return FileResponse(
        output_path,
        headers={"request-query": json.dumps({"input_path": str(input_path)})},  # not really needed
        media_type="application/octet-stream",
        filename=output_path.name,
        background=BackgroundTask(cleanup),
    )


@app.get("/circuit/count")
def count(
    input_path: Path = Depends(_validate_path),
    population_name: Optional[List[str]] = Query(default=None),
) -> Dict:
    """Return the number of nodes in a circuit."""
    # not cpu intensive, it can run in the current thread
    return service.count(input_path=input_path, population_names=population_name)


def read_circuit_job(
    input_path: Path,
    population_name: Optional[str],
    sampling_ratio: float,
    modality_names: Optional[List[str]],
    regions: Optional[List[str]],
    mtypes: Optional[List[str]],
    seed: int,
    how: str,
    output_path: Path,
) -> None:
    """Function that can be pickled and executed in a subprocess."""
    df = service.export(
        input_path=input_path,
        population_name=population_name,
        sampling_ratio=sampling_ratio,
        modality_names=modality_names,
        regions=regions,
        mtypes=mtypes,
        seed=seed,
    )
    serialize.write(df=df, modality_names=modality_names, output_path=output_path, how=how)
