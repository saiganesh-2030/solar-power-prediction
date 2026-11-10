"""Pydantic schemas for /models and performance endpoints.

References:
- docs/ARCHITECTURE_AND_API.md section 3.5 & 5
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from backend.app.core.schemas_common import GenericSuccessEnvelope

class ModelItem(BaseModel):
    name: str = Field(..., description="Unique model identifier")
    display_name: str = Field(..., description="Human-readable model name")
    description: str = Field(..., description="Concise description of architecture and inputs")
    is_selected: bool = Field(default=False, description="Whether this is the currently selected model for the plant")

class ModelsListResponse(GenericSuccessEnvelope[List[ModelItem]]):
    pass

class ModelPerformanceData(BaseModel):
    capacity_proxy_kw: float
    selected_model: str
    selection_reason: str
    models: List[Dict[str, Any]]
    walk_forward: List[Dict[str, Any]]
    by_irradiation_bin: List[Dict[str, Any]]
    by_day_type: List[Dict[str, Any]]
    plant_level: Optional[Dict[str, Any]] = None

class ModelPerformanceResponse(GenericSuccessEnvelope[ModelPerformanceData]):
    pass

class ResidualPoint(BaseModel):
    irradiation_kw_m2: float
    residual_kw: float

class HistogramBin(BaseModel):
    bin_start: float
    bin_end: float
    count: int

class ModelResidualsData(BaseModel):
    histogram: List[HistogramBin]
    sample_points: List[ResidualPoint]
    mean_residual_kw: float
    std_residual_kw: float

class ModelResidualsResponse(GenericSuccessEnvelope[ModelResidualsData]):
    pass

class FeatureImportanceItem(BaseModel):
    feature: str
    importance: float
    explanation: Optional[str] = Field(
        default=None,
        description="Plain-language physical and engineering explanation of what this feature represents",
    )

class FeatureImportanceResponse(GenericSuccessEnvelope[List[FeatureImportanceItem]]):
    pass

