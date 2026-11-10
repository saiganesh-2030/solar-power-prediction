"""Application configuration settings for FastAPI backend.

References:
- docs/ARCHITECTURE_AND_API.md section 1 & 4
- docs/roles/ROLE_4_PLATFORM_INTEGRATION.md section 4
"""

import os
from pathlib import Path
from ml.common.config import (
    DEFAULT_TARIFF_INR_PER_KWH,
    REPO_ROOT,
    ARTIFACTS_DIR,
    STUB_DIR,
)

class Settings:
    PROJECT_NAME: str = "Solar Power Generation Prediction & Performance Deviation Analysis"
    API_V1_STR: str = "/api/v1"
    
    # Artifact directory resolution: default to artifacts/, fallback to artifacts/_stub
    ARTIFACT_DIR: Path = Path(os.getenv("ARTIFACT_DIR", str(ARTIFACTS_DIR))).resolve()
    STUB_DIR: Path = STUB_DIR.resolve()
    
    # CORS: Allow frontend dev server
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    
    DEFAULT_TARIFF: float = DEFAULT_TARIFF_INR_PER_KWH

settings = Settings()

