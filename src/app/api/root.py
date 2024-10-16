"""Root API."""

from http.client import responses

from fastapi import APIRouter, Depends
from starlette.responses import JSONResponse, RedirectResponse
from starlette.status import HTTP_302_FOUND

from app import nexus
from app.config import settings
from app.dependencies import NexusConfigDep, no_cache

router = APIRouter()


@router.get("/")
async def root():
    """Root endpoint."""
    return RedirectResponse(url=f"{settings.ROOT_PATH}/docs", status_code=HTTP_302_FOUND)


@router.get("/health", dependencies=[Depends(no_cache)])
async def health() -> dict:
    """Health endpoint."""
    return {
        "status": "OK",
    }


@router.get("/version", dependencies=[Depends(no_cache)])
async def version() -> dict:
    """Version endpoint."""
    return {
        "app_name": settings.APP_NAME,
        "app_version": settings.APP_VERSION,
        "commit_sha": settings.COMMIT_SHA,
    }


@router.get("/auth", include_in_schema=False)
def auth(
    nexus_config: NexusConfigDep,
) -> JSONResponse:
    """Auth endpoint."""
    status_code = nexus.is_user_authorized(nexus_config)
    return JSONResponse(
        content={"message": responses[status_code]},
        status_code=status_code,
    )
