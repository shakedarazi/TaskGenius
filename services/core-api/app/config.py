"""
TASKGENIUS Core API - Configuration Module

This module handles application configuration via environment variables.
"""

import os
from typing import Optional


class Settings:
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = "TASKGENIUS Core API"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # Server
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    # MongoDB
    MONGODB_URI: str = os.getenv("MONGODB_URI", "mongodb://mongodb:27017")
    MONGODB_DATABASE: str = os.getenv("MONGODB_DATABASE", "taskgenius")

    # Chatbot Service
    CHATBOT_SERVICE_URL: str = os.getenv(
        "CHATBOT_SERVICE_URL", "http://chatbot-service:8001"
    )

    # CORS - Allowed origins for client requests
    # In production, set to specific origins like "https://taskgenius.example.com"
    # Multiple origins can be comma-separated
    CORS_ORIGINS: list[str] = [
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")
        if origin.strip()
    ]

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")


settings = Settings()
