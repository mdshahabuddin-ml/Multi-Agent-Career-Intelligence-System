"""Audit logging for security events."""

import json
import logging
import threading
from datetime import datetime
from typing import Any, Dict, Optional, List
from dataclasses import dataclass, field, asdict
from enum import Enum
from contextvars import ContextVar

from backend.security.config import get_security_config


class AuditEventType(Enum):
    """Types of audit events."""
    # Authentication
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    LOGOUT = "logout"
    TOKEN_REFRESH = "token_refresh"
    PASSWORD_CHANGE = "password_change"
    PASSWORD_RESET_REQUEST = "password_reset_request"
    PASSWORD_RESET_COMPLETE = "password_reset_complete"

    # Authorization
    ACCESS_DENIED = "access_denied"
    PERMISSION_CHANGED = "permission_changed"
    ROLE_ASSIGNED = "role_assigned"
    ROLE_REVOKED = "role_revoked"

    # API Keys
    API_KEY_CREATED = "api_key_created"
    API_KEY_REVOKED = "api_key_revoked"
    API_KEY_ROTATED = "api_key_rotated"
    API_KEY_USED = "api_key_used"

    # Data Access
    DATA_VIEWED = "data_viewed"
    DATA_EXPORTED = "data_exported"
    DATA_DELETED = "data_deleted"
    DATA_MODIFIED = "data_modified"
    BULK_DATA_ACCESS = "bulk_data_access"

    # Security
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    IP_BLOCKED = "ip_blocked"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    CSRF_VIOLATION = "csrf_violation"
    INVALID_INPUT = "invalid_input"

    # System
    CONFIG_CHANGED = "config_changed"
    BACKUP_CREATED = "backup_created"
    MAINTENANCE_STARTED = "maintenance_started"


class AuditSeverity(Enum):
    """Audit event severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """Audit event record."""
    event_type: AuditEventType
    severity: AuditSeverity
    user_id: Optional[int] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    action: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    request_id: Optional[str] = None
    session_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data["event_type"] = self.event_type.value
        data["severity"] = self.severity.value
        data["timestamp"] = self.timestamp.isoformat()
        return data

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), default=str)


# Context variable for request tracking
request_context: ContextVar[Dict[str, Any]] = ContextVar("request_context", default={})


class AuditLogger:
    """Audit logger for security events."""

    def __init__(self, config=None):
        self.config = config or get_security_config()
        self.logger = logging.getLogger("audit")
        self._setup_logger()

        # Buffer for batch writing
        self._buffer: List[AuditEvent] = []
        self._buffer_lock = threading.Lock()
        self._buffer_size = 100
        self._flush_interval = 5  # seconds

    def _setup_logger(self):
        """Set up the audit logger."""
        self.logger.setLevel(logging.INFO)

        # Avoid duplicate handlers
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - AUDIT - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.propagate = False

    def log(self, event: AuditEvent):
        """Log an audit event."""
        if not self.config.AUDIT_LOG_ENABLED:
            return

        # Sanitize sensitive fields
        sanitized_details = self._sanitize_details(event.details)
        event.details = sanitized_details

        # Add request context if available
        context = request_context.get()
        if context:
            event.request_id = context.get("request_id")
            event.session_id = context.get("session_id")
            if not event.ip_address:
                event.ip_address = context.get("ip_address")
            if not event.user_agent:
                event.user_agent = context.get("user_agent")

        # Log to structured logger
        self.logger.info(event.to_json())

        # Buffer for batch processing
        with self._buffer_lock:
            self._buffer.append(event)
            if len(self._buffer) >= self._buffer_size:
                self._flush_buffer()

    def _sanitize_details(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """Remove sensitive fields from details."""
        sanitized = {}
        sensitive_fields = set(self.config.AUDIT_LOG_SENSITIVE_FIELDS)

        for key, value in details.items():
            key_lower = key.lower()
            if any(sensitive in key_lower for sensitive in sensitive_fields):
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_details(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    self._sanitize_details(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                sanitized[key] = value

        return sanitized

    def _flush_buffer(self):
        """Flush buffer to persistent storage."""
        # In production, write to database, file, or streaming service
        # For now, just clear buffer
        self._buffer.clear()

    # Convenience methods for common events

    def log_login_success(self, user_id: int, ip: str, user_agent: str, **details):
        """Log successful login."""
        self.log(AuditEvent(
            event_type=AuditEventType.LOGIN_SUCCESS,
            severity=AuditSeverity.LOW,
            user_id=user_id,
            ip_address=ip,
            user_agent=user_agent,
            action="login",
            details=details,
        ))

    def log_login_failure(self, ip: str, user_agent: str, email: str, reason: str, **details):
        """Log failed login attempt."""
        self.log(AuditEvent(
            event_type=AuditEventType.LOGIN_FAILURE,
            severity=AuditSeverity.MEDIUM,
            ip_address=ip,
            user_agent=user_agent,
            action="login",
            details={"email": email, "reason": reason, **details},
        ))

    def log_access_denied(self, user_id: int, ip: str, resource: str, action: str, **details):
        """Log access denied."""
        self.log(AuditEvent(
            event_type=AuditEventType.ACCESS_DENIED,
            severity=AuditSeverity.HIGH,
            user_id=user_id,
            ip_address=ip,
            resource_type=resource,
            action=action,
            details=details,
        ))

    def log_data_access(self, user_id: int, resource_type: str, resource_id: str,
                        action: str, ip: str, **details):
        """Log data access."""
        severity = AuditSeverity.MEDIUM
        if action in ("export", "bulk_read"):
            severity = AuditSeverity.HIGH

        self.log(AuditEvent(
            event_type=AuditEventType.DATA_VIEWED if action == "view" else AuditEventType.DATA_EXPORTED,
            severity=severity,
            user_id=user_id,
            ip_address=ip,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            details=details,
        ))

    def log_api_key_event(self, event_type: AuditEventType, user_id: int, key_id: str,
                          ip: str, **details):
        """Log API key event."""
        self.log(AuditEvent(
            event_type=event_type,
            severity=AuditSeverity.MEDIUM,
            user_id=user_id,
            ip_address=ip,
            resource_type="api_key",
            resource_id=key_id,
            action=event_type.value,
            details=details,
        ))

    def log_rate_limit_exceeded(self, ip: str, endpoint: str, limit: int, **details):
        """Log rate limit exceeded."""
        self.log(AuditEvent(
            event_type=AuditEventType.RATE_LIMIT_EXCEEDED,
            severity=AuditSeverity.HIGH,
            ip_address=ip,
            action="rate_limit",
            details={"endpoint": endpoint, "limit": limit, **details},
        ))

    def log_suspicious_activity(self, ip: str, user_id: Optional[int], activity: str, **details):
        """Log suspicious activity."""
        self.log(AuditEvent(
            event_type=AuditEventType.SUSPICIOUS_ACTIVITY,
            severity=AuditSeverity.CRITICAL,
            user_id=user_id,
            ip_address=ip,
            action="suspicious",
            details={"activity": activity, **details},
        ))


# Global audit logger instance
audit_logger = AuditLogger()


def get_audit_logger() -> AuditLogger:
    """Get the audit logger instance."""
    return audit_logger


def set_request_context(context: Dict[str, Any]):
    """Set request context for audit logging."""
    request_context.set(context)


def clear_request_context():
    """Clear request context."""
    request_context.set({})


class AuditMiddleware:
    """Middleware to automatically log requests."""

    def __init__(self, app, config=None):
        self.app = app
        self.config = config or get_security_config()
        self.audit_logger = get_audit_logger()

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Extract request info
        request_id = scope.get("headers", {}).get(b"x-request-id", b"").decode()
        if not request_id:
            import uuid
            request_id = str(uuid.uuid4())[:8]

        client_ip = scope.get("client", ["unknown"])[0]
        user_agent = dict(scope.get("headers", {})).get(b"user-agent", b"").decode()

        # Set request context
        context = {
            "request_id": request_id,
            "ip_address": client_ip,
            "user_agent": user_agent,
            "method": scope["method"],
            "path": scope["path"],
        }
        set_request_context(context)

        # Track response status
        response_status = [200]

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                response_status[0] = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            # Log request
            # In production, get user_id from auth
            self.audit_logger.log(AuditEvent(
                event_type=AuditEventType.DATA_VIEWED,
                severity=AuditSeverity.LOW,
                ip_address=client_ip,
                user_agent=user_agent,
                action="http_request",
                details={
                    "method": scope["method"],
                    "path": scope["path"],
                    "status_code": response_status[0],
                },
                request_id=request_id,
            ))
            clear_request_context()