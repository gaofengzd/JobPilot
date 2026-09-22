"""Transport-only health endpoint; it does not initialize model services."""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "jobpilot-api", "version": "1.0.0"}
