"""Router for Feature 2: Solar Power Prediction.

Endpoints:
- POST /api/v1/predict
- GET /api/v1/predictions/timeseries

References:
- docs/roles/ROLE_1_ML_ENGINEER.md
- docs/ARCHITECTURE_AND_API.md section 5 & 6
"""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Query

from backend.app.core.data_store import data_store
from backend.app.core.schemas_common import MetaEnvelope
from backend.app.schemas.predict import (
    PredictRequest,
    PredictResponse,
    PredictionsTimeSeriesResponse,
)
from backend.app.services.prediction_service import (
    compute_single_prediction,
    get_predictions_timeseries,
)

router = APIRouter(tags=["Prediction"])

@router.post("/predict", response_model=PredictResponse)
def post_predict(req: PredictRequest) -> PredictResponse:
    """Estimates expected AC power per inverter and plant total for given weather conditions."""
    data = compute_single_prediction(req)
    return PredictResponse(
        data=data,
        meta=MetaEnvelope(
            plant=req.plant,
            model_name=data.model_name,
            generated_at=datetime.utcnow().isoformat(timespec="seconds"),
            source=data_store.source,
        ),
    )

@router.get("/predictions/timeseries", response_model=PredictionsTimeSeriesResponse)
def get_timeseries(
    plant: int = Query(default=1, description="Plant ID (1 or 2)"),
    start: Optional[str] = Query(default=None, description="Start date YYYY-MM-DD"),
    end: Optional[str] = Query(default=None, description="End date YYYY-MM-DD"),
    inverter: Optional[str] = Query(default=None, description="Optional inverter ID"),
    split: Optional[str] = Query(default=None, description="train, val, test, or all"),
) -> PredictionsTimeSeriesResponse:
    """Returns actual vs expected generation time series with normal band edges."""
    clean_plant = int(plant) if not hasattr(plant, "default") else 1
    clean_start = str(start) if start and not hasattr(start, "default") else None
    clean_end = str(end) if end and not hasattr(end, "default") else None
    clean_inv = str(inverter) if inverter and not hasattr(inverter, "default") else None
    clean_split = str(split) if split and not hasattr(split, "default") else None

    data = get_predictions_timeseries(
        plant=clean_plant,
        start=clean_start,
        end=clean_end,
        inverter=clean_inv,
        split=clean_split,
    )

    return PredictionsTimeSeriesResponse(
        data=data,
        meta=MetaEnvelope(
            plant=clean_plant,
            start=clean_start,
            end=clean_end,
            split=clean_split or "all",
            generated_at=datetime.utcnow().isoformat(timespec="seconds"),
            source=data_store.source,
        ),
    )

