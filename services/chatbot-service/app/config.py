"""
TASKGENIUS Chatbot Service - Configuration Module

This module handles application configuration via environment variables.
"""

import os


class Settings:
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = "TASKGENIUS Chatbot Service"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # Server
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8001"))

    # Core API (for callbacks if needed)
    CORE_API_URL: str = os.getenv("CORE_API_URL", "http://core-api:8000")

    # AI/LLM Configuration (placeholder for future phases)
    # OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    # MODEL_NAME: str = os.getenv("MODEL_NAME", "gpt-4")

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")


settings = Settings()
