"""Web api."""

from fastapi import APIRouter

from app.api import auth, circuit, root

router = APIRouter()
router.include_router(root.router)
router.include_router(auth.router, prefix="/auth")
router.include_router(circuit.router, prefix="/circuit", tags=["circuit"])
