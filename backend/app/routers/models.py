"""Router for Feature 6: Model Performance and Diagnostics.

Endpoints:
- GET /api/v1/models
- GET /api/v1/models/performance
- GET /api/v1/models/residuals
- GET /api/v1/models/feature-importance

References:
- docs/roles/ROLE_1_ML_ENGINEER.md
- docs/ARCHITECTURE_AND_API.md section 3.5 & 5
"""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Query
import numpy as np

from backend.app.core.data_store import data_store
from backend.app.core.schemas_common import MetaEnvelope
from backend.app.schemas.models import (
    FeatureImportanceItem,
    FeatureImportanceResponse,
    HistogramBin,
    ModelItem,
    ModelPerformanceData,
    ModelPerformanceResponse,
    ModelResidualsData,
    ModelResidualsResponse,
    ModelsListResponse,
    ResidualPoint,
)
from backend.app.services.prediction_service import MODEL_DESCRIPTIONS

router = APIRouter(prefix="/models", tags=["Models"])

FEATURE_EXPLANATIONS = {
    "irradiation_kw_m2": "Direct solar irradiance driving photovoltaic electron generation; primary physical power source.",
    "module_temp_c": "PV panel surface temperature; higher temperature induces negative thermal voltage drop.",
    "ambient_temp_c": "Surrounding air temperature; determines convective panel cooling efficiency.",
    "temp_delta_c": "Difference between module and ambient temperature; proxy for solar heat absorption and wind cooling.",
    "hour_sin": "Cyclical sine of time of day; encodes diurnal solar elevation angle smoothly.",
    "hour_cos": "Cyclical cosine of time of day; distinguishes morning ramp-up from afternoon ramp-down.",
    "irr_lag1": "Solar irradiance in previous 15-minute interval; captures short-term persistent cloud cover.",
    "irr_diff1": "Rate of change in irradiance; captures transient cloud shadows and rapid weather shifts.",
    "irr_roll_mean_4": "1-hour trailing average irradiance; represents steady-state solar regime.",
    "irr_roll_std_4": "1-hour trailing irradiance volatility; measures cloud intermittency and variability.",
    "irr_x_modtemp": "Interaction between irradiance and module temperature; captures irradiance-dependent thermal loss.",
}

@router.get("", response_model=ModelsListResponse)
def get_models(
    plant: int = Query(default=1, description="Plant ID (1 or 2)"),
) -> ModelsListResponse:
    """Returns list of models with descriptions and selection status."""
    clean_plant = int(plant) if not hasattr(plant, "default") else 1
    metrics = data_store.get_metrics()
    selected_name = metrics.get("plants", {}).get(str(clean_plant), {}).get("selected_model", "physics_baseline")

    items = []
    for m_id, info in MODEL_DESCRIPTIONS.items():
        items.append(
            ModelItem(
                name=m_id,
                display_name=info["display_name"],
                description=info["description"],
                is_selected=(m_id == selected_name),
            )
        )

    return ModelsListResponse(
        data=items,
        meta=MetaEnvelope(
            plant=clean_plant,
            model_name=selected_name,
            generated_at=datetime.utcnow().isoformat(timespec="seconds"),
            source=data_store.source,
        ),
    )

@router.get("/performance", response_model=ModelPerformanceResponse)
def get_model_performance(
    plant: int = Query(default=1, description="Plant ID (1 or 2)"),
) -> ModelPerformanceResponse:
    """Returns metrics table (all & daylight), walk-forward stability, and breakdowns."""
    clean_plant = int(plant) if not hasattr(plant, "default") else 1
    metrics = data_store.get_metrics()
    plant_metrics = metrics.get("plants", {}).get(str(clean_plant), {})

    data = ModelPerformanceData(
        capacity_proxy_kw=plant_metrics.get("capacity_proxy_kw", 850.0),
        selected_model=plant_metrics.get("selected_model", "physics_baseline"),
        selection_reason=plant_metrics.get("selection_reason", "Lowest validation daylight RMSE"),
        models=plant_metrics.get("models", []),
        walk_forward=plant_metrics.get("walk_forward", []),
        by_irradiation_bin=plant_metrics.get("by_irradiation_bin", []),
        by_day_type=plant_metrics.get("by_day_type", []),
    )

    return ModelPerformanceResponse(
        data=data,
        meta=MetaEnvelope(
            plant=clean_plant,
            model_name=data.selected_model,
            generated_at=datetime.utcnow().isoformat(timespec="seconds"),
            source=data_store.source,
        ),
    )

@router.get("/residuals", response_model=ModelResidualsResponse)
def get_model_residuals(
    plant: int = Query(default=1, description="Plant ID (1 or 2)"),
    split: Optional[str] = Query(default="test", description="Data split: test, val, or all"),
) -> ModelResidualsResponse:
    """Returns residual distribution histogram and residual vs irradiation diagnostic points."""
    clean_plant = int(plant) if not hasattr(plant, "default") else 1
    clean_split = str(split) if split and not hasattr(split, "default") else "test"

    preds_df = data_store.get_predictions(plant=clean_plant, split=clean_split)
    
    # Filter daylight rows with valid prediction and actual
    valid = preds_df[
        (preds_df["irradiation_kw_m2"] >= 0.05) &
        preds_df["ac_kw_actual"].notna() &
        preds_df["ac_kw_pred"].notna()
    ].copy()

    if valid.empty:
        return ModelResidualsResponse(
            data=ModelResidualsData(
                histogram=[],
                sample_points=[],
                mean_residual_kw=0.0,
                std_residual_kw=0.0,
            ),
            meta=MetaEnvelope(plant=clean_plant, split=clean_split),
        )

    residuals = valid["ac_kw_actual"].values - valid["ac_kw_pred"].values
    mean_res = float(np.mean(residuals))
    std_res = float(np.std(residuals))

    # Compute 15-bin histogram
    counts, bin_edges = np.histogram(residuals, bins=15)
    hist_bins = [
        HistogramBin(
            bin_start=round(float(bin_edges[i]), 2),
            bin_end=round(float(bin_edges[i + 1]), 2),
            count=int(counts[i]),
        )
        for i in range(len(counts))
    ]

    # Sample up to 150 points for scatter plot (residual vs irradiation)
    sample_n = min(150, len(valid))
    sampled = valid.sample(n=sample_n, random_state=42)
    sample_points = [
        ResidualPoint(
            irradiation_kw_m2=round(float(irr), 4),
            residual_kw=round(float(act - pred), 2),
        )
        for irr, act, pred in zip(sampled["irradiation_kw_m2"], sampled["ac_kw_actual"], sampled["ac_kw_pred"])
    ]

    data = ModelResidualsData(
        histogram=hist_bins,
        sample_points=sample_points,
        mean_residual_kw=round(mean_res, 2),
        std_residual_kw=round(std_res, 2),
    )

    return ModelResidualsResponse(
        data=data,
        meta=MetaEnvelope(
            plant=clean_plant,
            split=clean_split,
            generated_at=datetime.utcnow().isoformat(timespec="seconds"),
            source=data_store.source,
        ),
    )

@router.get("/feature-importance", response_model=FeatureImportanceResponse)
def get_feature_importance(
    plant: int = Query(default=1, description="Plant ID (1 or 2)"),
) -> FeatureImportanceResponse:
    """Returns permutation importance for features of the selected model."""
    clean_plant = int(plant) if not hasattr(plant, "default") else 1
    metrics = data_store.get_metrics()
    plant_metrics = metrics.get("plants", {}).get(str(clean_plant), {})
    feats = plant_metrics.get("feature_importance", [])

    items = [
        FeatureImportanceItem(
            feature=f["feature"],
            importance=f["importance"],
            explanation=f.get("explanation") or FEATURE_EXPLANATIONS.get(f["feature"], "Physical weather and temporal covariate."),
        )
        for f in feats
    ]

    return FeatureImportanceResponse(
        data=items,
        meta=MetaEnvelope(
            plant=clean_plant,
            model_name=plant_metrics.get("selected_model", "physics_baseline"),
            generated_at=datetime.utcnow().isoformat(timespec="seconds"),
            source=data_store.source,
        ),
    )

