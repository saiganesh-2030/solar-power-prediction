"""FastAPI application entry point and factory.

References:
- docs/ARCHITECTURE_AND_API.md section 1 & 4
- docs/roles/ROLE_4_PLATFORM_INTEGRATION.md Deliverable D2
"""

import importlib
import logging
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import settings
from backend.app.core.errors import (
    AppError,
    app_error_handler,
    general_exception_handler,
    validation_error_handler,
)
from backend.app.routers import health, meta

logger = logging.getLogger("uvicorn.error")

def create_app() -> FastAPI:
    """App factory creating and configuring the FastAPI instance."""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        description="REST API for solar power generation prediction and performance deviation analysis.",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # 1. CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 2. Exception Handlers conforming to Error Envelope
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(Exception, general_exception_handler)

    # 3. Core Routers (Health & Meta)
    # Liveness check available at /health and /api/v1/health
    app.include_router(health.router)
    app.include_router(health.router, prefix=settings.API_V1_STR)
    app.include_router(meta.router, prefix=settings.API_V1_STR)

    # 4. Optional Routers (dynamically loaded; tolerates missing role routers)
    optional_routers = [
        ("dashboard", "backend.app.routers.dashboard"),
        ("predict", "backend.app.routers.predict"),
        ("models", "backend.app.routers.models"),
        ("anomalies", "backend.app.routers.anomalies"),
        ("weather", "backend.app.routers.weather"),
        ("history", "backend.app.routers.history"),
        ("finance", "backend.app.routers.finance"),
    ]

    for name, module_path in optional_routers:
        try:
            mod = importlib.import_module(module_path)
            if hasattr(mod, "router"):
                app.include_router(mod.router, prefix=settings.API_V1_STR)
                logger.info(f"Registered router: {name}")
        except ModuleNotFoundError:
            # Expected during early development before roles add their routers
            pass
        except Exception as e:
            logger.warning(f"Could not register router {name}: {e}")

    return app

app = create_app()

