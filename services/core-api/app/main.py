"""
TASKGENIUS Core API - Main Application

This is the primary backend service and system of record for TASKGENIUS.
It is the ONLY public-facing backend entrypoint.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import database
from app.auth import auth_router
from app.tasks import tasks_router
from app.insights import insights_router
from app.chat import chat_router
from app.telegram import telegram_router
from app.telegram.scheduler import WeeklySummaryScheduler
from app.security import validate_security_config

import logging

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown events."""
    # Startup: Validate security configuration
    validate_security_config()
    # Startup: Connect to MongoDB
    await database.connect()
    
    # Startup: Start weekly summary scheduler
    scheduler = WeeklySummaryScheduler(database.get_database())
    await scheduler.start()
    
    yield
    
    # Shutdown: Stop scheduler
    await scheduler.stop()
    # Shutdown: Disconnect from MongoDB
    await database.disconnect()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Task management platform with AI-powered insights",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)

# CORS configuration - allow client origins
# In development: http://localhost:5173 (Vite default)
# In production: configure via CORS_ORIGINS environment variable
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.get("/health", tags=["Health"])
async def health_check() -> dict:
    """
    Health check endpoint.
    
    Returns the service status and version information.
    Used by Docker health checks and load balancers.
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
        "docs": "/docs" if settings.DEBUG else "disabled",
    }


# Phase 1: Authentication router
app.include_router(auth_router)

# Phase 2: Tasks router
app.include_router(tasks_router)

# Phase 3: Insights router
app.include_router(insights_router)

# Phase 4: Chat router
app.include_router(chat_router)

# Phase 5: Telegram router
app.include_router(telegram_router)
