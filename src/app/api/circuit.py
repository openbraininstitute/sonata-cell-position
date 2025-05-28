"""Circuit API."""

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from starlette.responses import FileResponse

import app.jobs
import app.serialize
import app.service
from app.dependencies import CircuitRefDep, UserContextDep, make_temp_path
from app.schemas import CircuitRef, QueryParams, SampleParams

router = APIRouter()


@router.get("")
def read_circuit(
    nexus_config: UserContextDep,
    params: Annotated[QueryParams, Depends(QueryParams.from_simplified_params)],
    tmp_path: Annotated[Path, Depends(make_temp_path(prefix="output_"))],
) -> FileResponse:
    """Return information about a circuit (cacheable)."""
    return query(nexus_config=nexus_config, params=params, tmp_path=tmp_path)


@router.post("/query")
def query(
    nexus_config: UserContextDep,
    params: QueryParams,
    tmp_path: Annotated[Path, Depends(make_temp_path(prefix="output_"))],
) -> FileResponse:
    """Return information about a circuit."""
    circuit_ref = CircuitRef.from_params(circuit_id=params.circuit_id)
    content_type = app.serialize.get_content_type(params.how)
    extension = app.serialize.get_extension(params.how)
    output_path = tmp_path / f"output.{extension}"
    app.jobs.read_circuit_job(
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


@router.post("/sample")
def sample(
    nexus_config: UserContextDep,
    params: SampleParams,
    tmp_path: Annotated[Path, Depends(make_temp_path(prefix="output_"))],
) -> FileResponse:
    """Sample a node file."""
    circuit_ref = CircuitRef.from_params(circuit_id=params.circuit_id)
    output_path = tmp_path / f"sampled_{params.sampling_ratio}.h5"
    app.jobs.sample_job(
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


@router.get("/count")
def count(
    nexus_config: UserContextDep,
    circuit_ref: CircuitRefDep,
    population_name: str | None = None,
) -> dict:
    """Return the number of nodes in a circuit."""
    path = app.service.get_circuit_config_path(circuit_ref, nexus_config=nexus_config)
    return app.service.count(input_path=path, population_name=population_name)


@router.get("/attribute_names")
def get_attribute_names(
    nexus_config: UserContextDep,
    circuit_ref: CircuitRefDep,
    population_name: str | None = None,
) -> dict:
    """Return the attribute names of a circuit."""
    path = app.service.get_circuit_config_path(circuit_ref, nexus_config=nexus_config)
    return app.service.get_attribute_names(input_path=path, population_name=population_name)


@router.get("/attribute_dtypes")
def get_attribute_dtypes(
    nexus_config: UserContextDep,
    circuit_ref: CircuitRefDep,
    population_name: str | None = None,
) -> dict:
    """Return the attribute data types of a circuit."""
    path = app.service.get_circuit_config_path(circuit_ref, nexus_config=nexus_config)
    return app.service.get_attribute_dtypes(input_path=path, population_name=population_name)


@router.get("/attribute_values")
def get_attribute_values(
    nexus_config: UserContextDep,
    circuit_ref: CircuitRefDep,
    population_name: str | None = None,
    attribute_names: Annotated[list[str] | None, Query()] = None,
) -> dict:
    """Return the unique values of the attributes of a circuit."""
    path = app.service.get_circuit_config_path(circuit_ref, nexus_config=nexus_config)
    return app.service.get_attribute_values(
        input_path=path,
        population_name=population_name,
        attribute_names=attribute_names,
    )


@router.get("/node_sets")
def node_sets(
    nexus_config: UserContextDep,
    circuit_ref: CircuitRefDep,
) -> dict:
    """Return the sorted list of node_sets in a circuit."""
    path = app.service.get_circuit_config_path(circuit_ref, nexus_config=nexus_config)
    return app.service.get_node_set_names(input_path=path)
