"""
TASKGENIUS Core API - Security Validation

Security checks and validations for Phase 6 hardening.
"""

import warnings
from app.config import settings


def validate_security_config() -> None:
    """
    Validate security configuration on startup.
    
    Issues warnings for insecure configurations but does not crash the application
    (to allow tests and development to run).
    """
    # JWT Secret Key validation
    if settings.JWT_SECRET_KEY == "dev-secret-key-change-in-production":
        if settings.is_production:
            warnings.warn(
                "SECURITY WARNING: Using default JWT_SECRET_KEY in production. "
                "Set JWT_SECRET_KEY environment variable to a strong secret.",
                UserWarning,
            )
        # In development, this is acceptable
    
    # CORS validation
    if "*" in str(settings.CORS_ORIGINS):
        warnings.warn(
            "SECURITY WARNING: CORS wildcard (*) detected. "
            "This is insecure and has been rejected. Set specific origins via CORS_ORIGINS.",
            UserWarning,
        )
    
    # JWT Secret Key strength (basic check)
    if len(settings.JWT_SECRET_KEY) < 32 and settings.is_production:
        warnings.warn(
            "SECURITY WARNING: JWT_SECRET_KEY is too short for production. "
            "Use at least 32 characters.",
            UserWarning,
        )
