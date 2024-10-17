"""Auth API."""

from http.client import responses

from fastapi import APIRouter
from starlette.responses import JSONResponse

from app import nexus
from app.dependencies import NexusConfigDep

router = APIRouter()


@router.get("", include_in_schema=False)
def auth(
    nexus_config: NexusConfigDep,
) -> JSONResponse:
    """Auth endpoint."""
    status_code = nexus.is_user_authorized(nexus_config)
    return JSONResponse(
        content={"message": responses[status_code]},
        status_code=status_code,
    )
