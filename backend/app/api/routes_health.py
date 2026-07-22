"""Health check endpoint — used by Docker HEALTHCHECK and the frontend status indicator."""
from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict:
    return {"status": "ok", "service": "sentinel-backend"}
