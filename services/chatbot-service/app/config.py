import os
from typing import Optional


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

    # AI/LLM Configuration (Phase 1)
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY", None)
    MODEL_NAME: str = os.getenv("MODEL_NAME", "gpt-4o-mini")
    USE_LLM: bool = os.getenv("USE_LLM", "false").lower() == "true"
    LLM_MODE: str = os.getenv("LLM_MODE", "nlg_only")
    LLM_TIMEOUT: float = float(os.getenv("LLM_TIMEOUT", "10.0"))

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")


settings = Settings()
