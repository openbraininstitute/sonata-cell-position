"""Auth API."""

from http.client import responses

from fastapi import APIRouter
from starlette.responses import JSONResponse

import app.auth
from app.dependencies import UserContextDep

router = APIRouter()


@router.get("", include_in_schema=False)
def auth(
    user_context: UserContextDep,
) -> JSONResponse:
    """Auth endpoint."""
    status_code = app.auth.is_user_authorized(user_context)
    return JSONResponse(
        content={"message": responses[status_code]},
        status_code=status_code,
    )
