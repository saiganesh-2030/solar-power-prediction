"""Metadata router providing plant and configuration info to frontend.

References:
- docs/ARCHITECTURE_AND_API.md section 5
- docs/roles/ROLE_4_PLATFORM_INTEGRATION.md section 4
"""

from datetime import datetime
from fastapi import APIRouter
from backend.app.core.data_store import data_store
from backend.app.core.schemas_common import MetaEnvelope
from backend.app.schemas.meta import MetaData, MetaResponse

router = APIRouter(prefix="/meta", tags=["Metadata"])

@router.get("", response_model=MetaResponse)
def get_meta() -> MetaResponse:
    info = data_store.get_meta_info()
    return MetaResponse(
        data=MetaData(
            plants=info["plants"],
            inverters=info["inverters"],
            date_range=info["date_range"],
            split_dates=info["split_dates"],
            selected_models=info["selected_models"],
            tariff_default=info["tariff_default"],
            data_version=info["data_version"],
            source=info["source"],
        ),
        meta=MetaEnvelope(
            generated_at=datetime.utcnow().isoformat(timespec="seconds"),
            source=info["source"],
        ),
    )

