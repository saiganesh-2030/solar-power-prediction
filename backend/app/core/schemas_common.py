"""Common Pydantic models for request and response envelopes.

References:
- docs/ARCHITECTURE_AND_API.md section 4
"""

from typing import Any, Generic, Optional, TypeVar
from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")

class MetaEnvelope(BaseModel):
    model_config = ConfigDict(extra="allow")
    
    plant: Optional[int] = Field(default=None, description="Plant ID (1 or 2)")
    start: Optional[str] = Field(default=None, description="Filter start date YYYY-MM-DD")
    end: Optional[str] = Field(default=None, description="Filter end date YYYY-MM-DD")
    split: Optional[str] = Field(default=None, description="Data split: train, val, test, or all")
    model_name: Optional[str] = Field(default=None, description="Name of the selected model")
    generated_at: Optional[str] = Field(default=None, description="ISO-8601 generation timestamp")
    source: Optional[str] = Field(default="artifacts", description="'artifacts' or 'stub'")

class GenericSuccessEnvelope(BaseModel, Generic[T]):
    data: T
    meta: MetaEnvelope = Field(default_factory=MetaEnvelope)

class ErrorDetail(BaseModel):
    code: str = Field(..., description="Error code enum: invalid_parameter, not_found, artifact_missing, internal_error")
    message: str = Field(..., description="Human-readable explanation")
    details: Optional[dict[str, Any]] = Field(default=None, description="Contextual error fields")

class ErrorEnvelope(BaseModel):
    error: ErrorDetail

