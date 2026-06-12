"""Health check endpoint."""

from fastapi import APIRouter

router = APIRouter(prefix="", tags=["health"])


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}