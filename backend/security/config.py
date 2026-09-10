"""Security configuration and constants."""

from typing import List, Optional
from pydantic import BaseModel
from backend.config import settings


class SecurityConfig(BaseModel):
    """Security configuration settings."""

    # Rate limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW_SECONDS: int = 60
    RATE_LIMIT_BURST: int = 20

    # Lockout duration: 1 minute in development, 15 minutes in production.
    # This allows developers to recover quickly from accidental burst
    # triggers while keeping full protection in production.
    LOCKOUT_DURATION_MINUTES: int = 1 if settings.DEBUG else 15

    # CORS
    CORS_ALLOW_ORIGINS: List[str] = [
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]

    # Security headers
    SECURITY_HEADERS_ENABLED: bool = True
    HSTS_MAX_AGE: int = 31536000  # 1 year
    CSP_POLICY: str = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self' wss: https:;"
    X_FRAME_OPTIONS: str = "DENY"
    X_CONTENT_TYPE_OPTIONS: str = "nosniff"
    REFERRER_POLICY: str = "strict-origin-when-cross-origin"
    PERMISSIONS_POLICY: str = "geolocation=(), microphone=(), camera=()"

    # Input validation
    MAX_REQUEST_SIZE_MB: int = 10
    MAX_JSON_DEPTH: int = 10
    MAX_ARRAY_LENGTH: int = 1000
    ALLOWED_FILE_EXTENSIONS: List[str] = ["pdf", "doc", "docx", "txt", "png", "jpg", "jpeg"]
    MAX_FILE_SIZE_MB: int = 10

    # JWT
    JWT_ALGORITHM: str = settings.ALGORITHM
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = settings.ACCESS_TOKEN_EXPIRE_MINUTES
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_ISSUER: str = "careerintel.ai"
    JWT_AUDIENCE: str = "careerintel-api"

    # Password
    PASSWORD_MIN_LENGTH: int = 12
    PASSWORD_REQUIRE_UPPERCASE: bool = True
    PASSWORD_REQUIRE_LOWERCASE: bool = True
    PASSWORD_REQUIRE_DIGITS: bool = True
    PASSWORD_REQUIRE_SPECIAL: bool = True
    PASSWORD_HISTORY_COUNT: int = 5

    # API Keys
    API_KEY_ENABLED: bool = True
    API_KEY_PREFIX: str = "ci_"
    API_KEY_LENGTH: int = 32
    API_KEY_HASH_ALGORITHM: str = "sha256"

    # Session
    SESSION_TIMEOUT_MINUTES: int = 60
    SESSION_MAX_CONCURRENT: int = 5
    SESSION_ROTATE_ON_PRIVILEGE_CHANGE: bool = True

    # Audit
    AUDIT_LOG_ENABLED: bool = True
    AUDIT_LOG_SENSITIVE_FIELDS: List[str] = [
        "password", "token", "secret", "api_key", "authorization",
        "credit_card", "ssn", "phone", "address"
    ]

    # IP Security
    IP_WHITELIST: List[str] = []
    IP_BLACKLIST: List[str] = []
    MAX_FAILED_LOGIN_ATTEMPTS: int = 5

    # Content Security
    ENABLE_XSS_PROTECTION: bool = True
    ENABLE_CSRF_PROTECTION: bool = not settings.DEBUG
    CSRF_TOKEN_LENGTH: int = 32
    CSRF_COOKIE_NAME: str = "csrf_token"
    CSRF_HEADER_NAME: str = "X-CSRF-Token"

    # Testing
    TESTING: bool = False

    # Logging
    LOG_REQUESTS: bool = True
    LOG_RESPONSES: bool = True
    LOG_REQUEST_BODY: bool = False
    LOG_RESPONSE_BODY: bool = False
    LOG_EXCLUDED_PATHS: List[str] = [
        "/health",
        "/metrics",
        "/favicon.ico",
        "/docs",
        "/openapi.json",
        "/redoc",
    ]
    LOG_MAX_BODY_LENGTH: int = 10000


# Default security config
security_config = SecurityConfig()


def get_security_config() -> SecurityConfig:
    """Get security configuration."""
    return security_config