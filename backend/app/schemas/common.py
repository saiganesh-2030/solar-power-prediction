"""Common schemas re-export for router schemas.

References:
- docs/roles/ROLE_4_PLATFORM_INTEGRATION.md section 2
"""

from backend.app.core.schemas_common import (
    MetaEnvelope,
    GenericSuccessEnvelope,
    ErrorDetail,
    ErrorEnvelope,
)

__all__ = [
    "MetaEnvelope",
    "GenericSuccessEnvelope",
    "ErrorDetail",
    "ErrorEnvelope",
]

