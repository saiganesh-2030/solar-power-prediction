"""Pydantic schemas for the /meta endpoint.

References:
- docs/ARCHITECTURE_AND_API.md section 5
- docs/roles/ROLE_4_PLATFORM_INTEGRATION.md section 4
"""

from typing import Any, Optional
from pydantic import BaseModel, Field
from backend.app.core.schemas_common import GenericSuccessEnvelope

class DateRange(BaseModel):
    start: str = Field(..., description="Earliest available date YYYY-MM-DD")
    end: str = Field(..., description="Latest available date YYYY-MM-DD")

class SplitDates(BaseModel):
    train: list[str] = Field(..., description="Train date block [start, end]")
    val: list[str] = Field(..., description="Validation date block [start, end]")
    test: list[str] = Field(..., description="Test date block [start, end]")

class MetaData(BaseModel):
    plants: list[int] = Field(..., description="Available plant IDs")
    inverters: dict[str, list[str]] = Field(..., description="Inverter IDs per plant")
    date_range: DateRange = Field(..., description="Overall dataset date range")
    split_dates: SplitDates = Field(..., description="Chronological split dates")
    selected_models: dict[str, str] = Field(..., description="Selected model name per plant")
    tariff_default: float = Field(..., description="Default tariff in INR per kWh")
    data_version: str = Field(..., description="Artifacts version or hash")
    source: str = Field(..., description="'artifacts' or 'stub'")

class MetaResponse(GenericSuccessEnvelope[MetaData]):
    pass

