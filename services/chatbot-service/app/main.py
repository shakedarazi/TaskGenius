"""
TASKGENIUS Chatbot Service - Main Application

This is the internal conversational interpretation layer.
It is accessible ONLY from core-api via internal HTTP.

IMPORTANT: This service must NEVER access MongoDB directly.
All data operations must go through core-api.
"""

import logging
from fastapi import FastAPI

from app.config import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Internal conversational interpretation layer for TASKGENIUS",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)


@app.get("/health", tags=["Health"])
async def health_check() -> dict:
    """
    Health check endpoint.
    
    Returns the service status and version information.
    Used by Docker health checks and internal monitoring.
    """
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


@app.get("/", tags=["Root"])
async def root() -> dict:
    """Root endpoint with service information."""
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "note": "Internal service - accessible only from core-api",
    }


# Phase 4: Interpret router
from app.router import router as interpret_router
app.include_router(interpret_router)
