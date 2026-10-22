# -*- coding: utf-8 -*-
"""Tax Automation FastAPI application factory.

Run with:
    uvicorn tax_automation.api.main:app --reload --host 0.0.0.0 --port 8000

Swagger UI:  http://localhost:8000/docs
ReDoc:       http://localhost:8000/redoc
"""

from __future__ import annotations
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from tax_automation.config_loader import load_env_file
from tax_automation.api.routers.entities import router as entities_router
from tax_automation.api.routers.pipeline import router as pipeline_router
from tax_automation.api.routers.diagnostics import router as diagnostics_router
from tax_automation.api.routers.files import router as files_router

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("tax_automation.api")


# ---------------------------------------------------------------------------
# App lifecycle
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load .env passwords on startup so encrypted statement decryption works."""
    loaded = load_env_file()
    logger.info(f"Loaded {len(loaded)} environment variable(s) from .env")
    yield
    logger.info("Tax Automation API shutting down.")


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------
def create_app() -> FastAPI:
    app = FastAPI(
        title="Tax Automation API",
        description=(
            "Config-driven financial transaction processing & consolidation engine. "
            "Consolidates bank statements, classifies transactions, and generates "
            "narrated Excel ledgers for Indian taxpayers."
        ),
        version="2.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # CORS — allow all origins locally; tighten in production
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routers
    app.include_router(entities_router)
    app.include_router(pipeline_router)
    app.include_router(diagnostics_router)
    app.include_router(files_router)

    # ---------------------------------------------------------------------------
    # Root health check
    # ---------------------------------------------------------------------------
    @app.get("/", tags=["Health"], summary="Health check")
    async def root():
        return {
            "service": "Tax Automation API",
            "version": "2.0.0",
            "status": "healthy",
            "docs": "/docs",
        }

    @app.get("/health", tags=["Health"], summary="Liveness probe")
    async def health():
        return {"status": "ok"}

    return app


app = create_app()
