"""Pydantic schemas for the dashboard overview endpoint.

References:
- docs/ARCHITECTURE_AND_API.md section 6
- docs/roles/ROLE_4_PLATFORM_INTEGRATION.md section 4
"""

from typing import Optional
from pydantic import BaseModel, Field
from backend.app.core.schemas_common import GenericSuccessEnvelope

class AnomalyCounts(BaseModel):
    total: int = 0
    shortfall: int = 0
    surplus: int = 0
    high_severity: int = 0

class ShortfallTiers(BaseModel):
    conservative: float = 0.0
    central: float = 0.0
    upper: float = 0.0

class ModelSummary(BaseModel):
    name: str = "hist_gradient_boosting"
    test_daylight_rmse_kw: float = 0.0
    test_daylight_r2: float = 0.0
    test_daylight_mae_kw: float = 0.0

class DashboardKPIs(BaseModel):
    actual_kwh: float = 0.0
    predicted_kwh: float = 0.0
    deviation_pct: float = 0.0
    anomaly_events: AnomalyCounts = Field(default_factory=AnomalyCounts)
    shortfall_kwh: ShortfallTiers = Field(default_factory=ShortfallTiers)
    shortfall_inr: ShortfallTiers = Field(default_factory=ShortfallTiers)
    tariff_inr_per_kwh: float = 4.0
    model: ModelSummary = Field(default_factory=ModelSummary)
    data_quality_score: float = 100.0

class PlantTimeSeries(BaseModel):
    t: list[str] = Field(default_factory=list)
    actual_kw: list[float] = Field(default_factory=list)
    pred_kw: list[float] = Field(default_factory=list)
    band_lo_kw: list[float] = Field(default_factory=list)
    band_hi_kw: list[float] = Field(default_factory=list)

class EventSpan(BaseModel):
    event_id: str
    start: str
    end: str
    direction: str
    category: str

class CandidateInverter(BaseModel):
    inverter_id: str
    events: int
    shortfall_kwh: float
    mean_peer_ratio: float
    confidence: str

class DashboardOverviewData(BaseModel):
    kpis: DashboardKPIs
    timeseries: PlantTimeSeries = Field(default_factory=PlantTimeSeries)
    event_spans: list[EventSpan] = Field(default_factory=list)
    top_candidates: list[CandidateInverter] = Field(default_factory=list)

class DashboardOverviewResponse(GenericSuccessEnvelope[DashboardOverviewData]):
    pass

