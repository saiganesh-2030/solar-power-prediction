"""Health check router for liveness and monitoring.

References:
- docs/ARCHITECTURE_AND_API.md section 5
"""

from fastapi import APIRouter

router = APIRouter(tags=["Health"])

@router.get("/health")
def get_health() -> dict[str, str]:
    """Liveness probe endpoint."""
    return {"status": "ok"}

