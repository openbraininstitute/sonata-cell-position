"""Caching functions."""
import hashlib
import json
import os
import shutil
import time
from pathlib import Path
from typing import Optional, TypedDict

from app import service
from app.constants import CACHE_CHECK_INTERVAL, CACHE_CHECK_TIMEOUT, SAMPLING_RATIO
from app.logger import L
from app.utils import modality_names_to_columns


class CacheParams(TypedDict, total=False):
    """Cache parameters."""

    input_path: Path
    population_name: Optional[str]
    sampling_ratio: float
    seed: int


def check_cache(
    input_path: Path,
    population_name: Optional[str],
    sampling_ratio: float,
    seed: int,
) -> CacheParams:
    """Read or write the cache."""
    if sampling_ratio > SAMPLING_RATIO:
        L.info(
            f"Not using the cache because the sampling_ratio {sampling_ratio} "
            f"is greater than {SAMPLING_RATIO}"
        )
        return {}

    metadata = json.dumps(
        {
            "input_path": str(input_path),
            "population_name": population_name,
            "sampling_ratio": SAMPLING_RATIO,
            "seed": seed,
        }
    )
    checksum = hashlib.sha256(metadata.encode("utf-8")).hexdigest()
    tmp_dir = Path(os.getenv("TMPDIR", "/tmp"), "cached_circuits", checksum)
    tmp_nodes = tmp_dir / "nodes.h5"
    tmp_metadata = tmp_dir / "metadata.json"
    tmp_ok = tmp_dir / "OK"
    try:
        tmp_dir.mkdir(parents=True, exist_ok=False)
    except OSError:
        if not tmp_dir.is_dir():
            raise
        cached = True
    else:
        cached = False
    if cached:
        L.info(f"Reading cache {checksum}")
        counter = CACHE_CHECK_TIMEOUT // CACHE_CHECK_INTERVAL
        while not tmp_ok.exists() and counter > 0:
            time.sleep(CACHE_CHECK_INTERVAL)
            counter -= 1
        if not tmp_ok.exists():
            raise RuntimeError("Timeout when waiting to read the cache")
    else:
        L.info(f"Writing cache {checksum}")
        try:
            tmp_metadata.write_text(metadata, encoding="utf-8")
            attributes = modality_names_to_columns()
            service.downsample(
                input_path=input_path,
                output_path=tmp_nodes,
                population_name=population_name,
                sampling_ratio=SAMPLING_RATIO,
                seed=seed,
                attributes=attributes,
            )
            tmp_ok.touch(exist_ok=False)
        except BaseException:
            L.error("Failure to write the cache, removing any temporary file")
            shutil.rmtree(tmp_dir)
            raise
    return {
        "input_path": tmp_nodes,
        "sampling_ratio": sampling_ratio / SAMPLING_RATIO,
    }
