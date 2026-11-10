"""Pydantic schemas for /predict and /predictions/timeseries.

References:
- docs/ARCHITECTURE_AND_API.md section 6
"""

from typing import List, Optional
from pydantic import BaseModel, Field
from backend.app.core.schemas_common import GenericSuccessEnvelope

class PredictRequest(BaseModel):
    plant: int = Field(default=1, ge=1, le=2, description="Plant ID (1 or 2)")
    timestamp: str = Field(default="2020-06-10T12:00:00", description="ISO-8601 timestamp")
    irradiation_kw_m2: float = Field(..., ge=0.0, le=1.5, description="Solar irradiance in kW/m2 [0.0 - 1.5]")
    module_temp_c: float = Field(..., ge=-10.0, le=90.0, description="Module temperature in deg C [-10 - 90]")
    ambient_temp_c: float = Field(..., ge=-10.0, le=60.0, description="Ambient temperature in deg C [-10 - 60]")
    model: str = Field(default="selected", description="Model name or 'selected'")

class PredictData(BaseModel):
    ac_kw_per_inverter: float = Field(..., description="Estimated AC power per inverter in kW")
    interval_lo_kw: float = Field(..., description="Conformal prediction interval lower bound in kW")
    interval_hi_kw: float = Field(..., description="Conformal prediction interval upper bound in kW")
    interval_coverage: float = Field(default=0.90, description="Prediction interval nominal coverage")
    plant_ac_kw_estimate: float = Field(..., description="Estimated plant total AC power (per_inverter * n_inverters)")
    n_inverters: int = Field(default=22, description="Number of inverters in plant")
    model_name: str = Field(..., description="Name of the model that produced the prediction")
    warnings: List[str] = Field(default_factory=list, description="Extrapolation or out-of-range warnings")

class PredictResponse(GenericSuccessEnvelope[PredictData]):
    pass

class PredictionsTimeSeriesData(BaseModel):
    t: List[str] = Field(default_factory=list, description="Column-oriented timestamps")
    actual_kw: List[Optional[float]] = Field(default_factory=list, description="Actual generation (kW)")
    pred_kw: List[Optional[float]] = Field(default_factory=list, description="Estimated expected power (kW)")
    band_lo_kw: List[Optional[float]] = Field(default_factory=list, description="Normal lower band (kW)")
    band_hi_kw: List[Optional[float]] = Field(default_factory=list, description="Normal upper band (kW)")

class PredictionsTimeSeriesResponse(GenericSuccessEnvelope[PredictionsTimeSeriesData]):
    pass

