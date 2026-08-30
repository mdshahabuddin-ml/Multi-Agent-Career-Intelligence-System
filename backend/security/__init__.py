"""Security module exports."""

from backend.security.config import SecurityConfig, security_config, get_security_config
from backend.security.middleware import (
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    RequestValidationMiddleware,
    CSRFProtectionMiddleware,
    generate_csrf_token,
)
from backend.security.api_keys import (
    APIKeyManager,
    APIKeyAuth,
    APIKeyScope,
    require_scopes,
)
from backend.security.audit import (
    AuditLogger,
    AuditEvent,
    AuditEventType,
    AuditSeverity,
    audit_logger,
    get_audit_logger,
    set_request_context,
    clear_request_context,
    AuditMiddleware,
)

__all__ = [
    # Config
    "SecurityConfig",
    "security_config",
    "get_security_config",
    # Middleware
    "RateLimitMiddleware",
    "SecurityHeadersMiddleware",
    "RequestValidationMiddleware",
    "CSRFProtectionMiddleware",
    "generate_csrf_token",
    # API Keys
    "APIKeyManager",
    "APIKeyAuth",
    "APIKeyScope",
    "require_scopes",
    # Audit
    "AuditLogger",
    "AuditEvent",
    "AuditEventType",
    "AuditSeverity",
    "audit_logger",
    "get_audit_logger",
    "set_request_context",
    "clear_request_context",
    "AuditMiddleware",
]