"""Router for Feature 1: Dashboard Overview.

References:
- docs/roles/ROLE_4_PLATFORM_INTEGRATION.md section 4
- docs/ARCHITECTURE_AND_API.md section 6
"""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Query
from backend.app.core.data_store import data_store
from backend.app.core.schemas_common import MetaEnvelope
from backend.app.schemas.dashboard import DashboardOverviewResponse
from backend.app.services.dashboard_service import compute_dashboard_overview

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/overview", response_model=DashboardOverviewResponse)
def get_dashboard_overview(
    plant: int = 1,
    start: Optional[str] = None,
    end: Optional[str] = None,
    split: Optional[str] = None,
) -> DashboardOverviewResponse:
    # Handle if called directly without kwargs or via FastAPI
    clean_start = str(start) if start and not hasattr(start, "default") else None
    clean_end = str(end) if end and not hasattr(end, "default") else None
    clean_split = str(split) if split and not hasattr(split, "default") else None
    clean_plant = int(plant) if not hasattr(plant, "default") else 1

    data = compute_dashboard_overview(
        plant=clean_plant,
        start=clean_start,
        end=clean_end,
        split=clean_split,
    )
    
    return DashboardOverviewResponse(
        data=data,
        meta=MetaEnvelope(
            plant=clean_plant,
            start=clean_start,
            end=clean_end,
            split=clean_split or "all",
            model_name=data.kpis.model.name,
            generated_at=datetime.utcnow().isoformat(timespec="seconds"),
            source=data_store.source,
        ),
    )
