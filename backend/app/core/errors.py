"""Application error classes and standardized error response handlers.

References:
- docs/ARCHITECTURE_AND_API.md section 4
"""

from typing import Any, Optional
from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

class AppError(Exception):
    """Base application exception conforming to API error contract."""
    def __init__(
        self,
        code: str = "internal_error",
        message: str = "An unexpected error occurred",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}

class InvalidParameterError(AppError):
    def __init__(self, message: str, details: Optional[dict[str, Any]] = None):
        super().__init__(
            code="invalid_parameter",
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details,
        )

class NotFoundError(AppError):
    def __init__(self, message: str, details: Optional[dict[str, Any]] = None):
        super().__init__(
            code="not_found",
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            details=details,
        )

class ArtifactMissingError(AppError):
    def __init__(self, message: str, details: Optional[dict[str, Any]] = None):
        super().__init__(
            code="artifact_missing",
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=details,
        )

async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            }
        },
    )

async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = exc.errors()
    first_error = errors[0] if errors else {}
    msg = first_error.get("msg", "Validation error")
    loc = first_error.get("loc", [])
    field = str(loc[-1]) if loc else "body"
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "invalid_parameter",
                "message": f"Invalid parameter '{field}': {msg}",
                "details": {"field": field, "errors": errors},
            }
        },
    )

async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "internal_error",
                "message": "An internal server error occurred",
                "details": {"type": type(exc).__name__, "message": str(exc)},
            }
        },
    )

