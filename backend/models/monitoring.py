from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional, List, Dict, Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, JSON, Float, Index, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class MetricType(str, PyEnum):
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


class AlertSeverity(str, PyEnum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class AlertStatus(str, PyEnum):
    FIRING = "firing"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SILENCED = "silenced"


class HealthStatus(str, PyEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class LogLevel(str, PyEnum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class TraceStatus(str, PyEnum):
    OK = "ok"
    ERROR = "error"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class Metric(Base):
    __tablename__ = "metrics"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    metric_type: Mapped[MetricType] = mapped_column(Enum(MetricType), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    labels: Mapped[Optional[Dict[str, str]]] = mapped_column(JSON, nullable=True)

    # Source
    source: Mapped[str] = mapped_column(String(100), nullable=False, index=True)  # service name
    source_instance: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)

    # Organization context
    organization_id: Mapped[Optional[int]] = mapped_column(ForeignKey("organizations.id"), nullable=True, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)

    # Time
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Metadata
    metric_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        Index('ix_metrics_name_timestamp', 'name', 'timestamp'),
        Index('ix_metrics_org_timestamp', 'organization_id', 'timestamp'),
    )


class AlertRule(Base):
    __tablename__ = "alert_rules"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Condition
    metric_name: Mapped[str] = mapped_column(String(255), nullable=False)
    condition: Mapped[str] = mapped_column(String(100), nullable=False)  # >, <, >=, <=, ==, !=
    threshold: Mapped[float] = mapped_column(Float, nullable=False)
    evaluation_window: Mapped[str] = mapped_column(String(50), default="5m", nullable=False)  # 5m, 15m, 1h, etc.

    # Labels to match
    label_filters: Mapped[Optional[Dict[str, str]]] = mapped_column(JSON, nullable=True)

    # Severity & Notification
    severity: Mapped[AlertSeverity] = mapped_column(Enum(AlertSeverity), default=AlertSeverity.WARNING, nullable=False)
    notification_channels: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)  # email, slack, pagerduty, webhook
    notification_template: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Cooldown
    cooldown_minutes: Mapped[int] = mapped_column(Integer, default=15, nullable=False)

    # Scope
    organization_id: Mapped[Optional[int]] = mapped_column(ForeignKey("organizations.id"), nullable=True, index=True)
    applies_to_all_orgs: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Status
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    organization: Mapped[Optional["Organization"]] = relationship("Organization")
    creator: Mapped["User"] = relationship("User", foreign_keys=[created_by])
    alerts: Mapped[list["Alert"]] = relationship("Alert", back_populates="rule", cascade="all, delete-orphan")


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    rule_id: Mapped[int] = mapped_column(ForeignKey("alert_rules.id"), nullable=False, index=True)

    # Alert details
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    severity: Mapped[AlertSeverity] = mapped_column(Enum(AlertSeverity), nullable=False)
    status: Mapped[AlertStatus] = mapped_column(Enum(AlertStatus), default=AlertStatus.FIRING, nullable=False, index=True)

    # Trigger details
    metric_name: Mapped[str] = mapped_column(String(255), nullable=False)
    metric_value: Mapped[float] = mapped_column(Float, nullable=False)
    threshold: Mapped[float] = mapped_column(Float, nullable=False)
    condition: Mapped[str] = mapped_column(String(100), nullable=False)
    labels: Mapped[Optional[Dict[str, str]]] = mapped_column(JSON, nullable=True)

    # Organization context
    organization_id: Mapped[Optional[int]] = mapped_column(ForeignKey("organizations.id"), nullable=True, index=True)

    # Timeline
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    acknowledged_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    resolved_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    silenced_until: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Metadata
    alert_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Relationships
    rule: Mapped["AlertRule"] = relationship("AlertRule", back_populates="alerts")
    organization: Mapped[Optional["Organization"]] = relationship("Organization")
    acknowledger: Mapped[Optional["User"]] = relationship("User", foreign_keys=[acknowledged_by])
    resolver: Mapped[Optional["User"]] = relationship("User", foreign_keys=[resolved_by])


class HealthCheck(Base):
    __tablename__ = "health_checks"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Check configuration
    check_type: Mapped[str] = mapped_column(String(50), nullable=False)  # http, tcp, database, custom, kafka, redis
    endpoint: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    interval_seconds: Mapped[int] = mapped_column(Integer, default=60, nullable=False)

    # Expected results
    expected_status: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    expected_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    custom_check: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Python code for custom check

    # Thresholds
    failure_threshold: Mapped[int] = mapped_column(Integer, default=3, nullable=False)  # consecutive failures before alert
    success_threshold: Mapped[int] = mapped_column(Integer, default=1, nullable=False)  # consecutive successes to recover

    # Organization scope
    organization_id: Mapped[Optional[int]] = mapped_column(ForeignKey("organizations.id"), nullable=True, index=True)
    is_global: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Status
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    current_status: Mapped[HealthStatus] = mapped_column(Enum(HealthStatus), default=HealthStatus.UNKNOWN, nullable=False)
    last_check_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_success_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_failure_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    consecutive_successes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Metadata
    health_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    organization: Mapped[Optional["Organization"]] = relationship("Organization")
    creator: Mapped["User"] = relationship("User", foreign_keys=[created_by])
    check_results: Mapped[list["HealthCheckResult"]] = relationship("HealthCheckResult", back_populates="check", cascade="all, delete-orphan")


class HealthCheckResult(Base):
    __tablename__ = "health_check_results"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    check_id: Mapped[int] = mapped_column(ForeignKey("health_checks.id"), nullable=False, index=True)

    # Result
    status: Mapped[HealthStatus] = mapped_column(Enum(HealthStatus), nullable=False)
    latency_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    response_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    response_body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timing
    checked_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Metadata
    result_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Relationships
    check: Mapped["HealthCheck"] = relationship("HealthCheck", back_populates="check_results")


class StructuredLog(Base):
    __tablename__ = "structured_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    level: Mapped[LogLevel] = mapped_column(Enum(LogLevel), nullable=False, index=True)

    # Source
    logger_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    service_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    instance_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Message
    message: Mapped[str] = mapped_column(Text, nullable=False)
    message_template: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Context
    trace_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    span_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    organization_id: Mapped[Optional[int]] = mapped_column(ForeignKey("organizations.id"), nullable=True, index=True)
    session_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    request_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)

    # Structured fields
    fields: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Exception info
    exception_type: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    exception_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    stack_trace: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index('ix_logs_timestamp_level', 'timestamp', 'level'),
        Index('ix_logs_org_timestamp', 'organization_id', 'timestamp'),
        Index('ix_logs_trace', 'trace_id'),
    )


class Trace(Base):
    __tablename__ = "traces"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    trace_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    parent_span_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)

    # Service info
    service_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    operation_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Timing
    start_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    duration_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Status
    status: Mapped[TraceStatus] = mapped_column(Enum(TraceStatus), default=TraceStatus.OK, nullable=False, index=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Context
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    organization_id: Mapped[Optional[int]] = mapped_column(ForeignKey("organizations.id"), nullable=True, index=True)
    request_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)

    # Tags & metadata
    tags: Mapped[Optional[Dict[str, str]]] = mapped_column(JSON, nullable=True)
    trace_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Relationships
    spans: Mapped[list["Span"]] = relationship("Span", back_populates="trace", cascade="all, delete-orphan")


class Span(Base):
    __tablename__ = "spans"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    trace_id: Mapped[str] = mapped_column(String(100), ForeignKey("traces.trace_id"), nullable=False, index=True)
    span_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    parent_span_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)

    # Service info
    service_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    operation_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Timing
    start_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    duration_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Status
    status: Mapped[TraceStatus] = mapped_column(Enum(TraceStatus), default=TraceStatus.OK, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Context
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    organization_id: Mapped[Optional[int]] = mapped_column(ForeignKey("organizations.id"), nullable=True, index=True)

    # Tags & metadata
    tags: Mapped[Optional[Dict[str, str]]] = mapped_column(JSON, nullable=True)
    span_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Relationships
    trace: Mapped["Trace"] = relationship("Trace", back_populates="spans")


class Dashboard(Base):
    __tablename__ = "dashboards"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    # Layout
    layout: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)  # Grid layout config

    # Scope
    organization_id: Mapped[Optional[int]] = mapped_column(ForeignKey("organizations.id"), nullable=True, index=True)
    is_global: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Access control
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    allowed_roles: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    allowed_users: Mapped[Optional[List[int]]] = mapped_column(JSON, nullable=True)

    # Metadata
    tags: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    organization: Mapped[Optional["Organization"]] = relationship("Organization")
    creator: Mapped["User"] = relationship("User", foreign_keys=[created_by])
    panels: Mapped[list["DashboardPanel"]] = relationship("DashboardPanel", back_populates="dashboard", cascade="all, delete-orphan")


class DashboardPanel(Base):
    __tablename__ = "dashboard_panels"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    dashboard_id: Mapped[int] = mapped_column(ForeignKey("dashboards.id"), nullable=False, index=True)

    # Panel config
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    panel_type: Mapped[str] = mapped_column(String(50), nullable=False)  # graph, stat, table, heatmap, logs, traces
    visualization: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)  # Panel-specific config

    # Query
    query: Mapped[str] = mapped_column(Text, nullable=False)
    metric_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    time_range: Mapped[str] = mapped_column(String(50), default="1h", nullable=False)

    # Layout
    x: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    y: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    width: Mapped[int] = mapped_column(Integer, default=6, nullable=False)
    height: Mapped[int] = mapped_column(Integer, default=4, nullable=False)

    # Styling
    options: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Relationships
    dashboard: Mapped["Dashboard"] = relationship("Dashboard", back_populates="panels")


class NotificationChannel(Base):
    __tablename__ = "notification_channels"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    channel_type: Mapped[str] = mapped_column(String(50), nullable=False)  # email, slack, webhook, pagerduty, sms

    # Configuration
    config: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)  # webhook_url, api_key, etc.
    default_severity: Mapped[AlertSeverity] = mapped_column(Enum(AlertSeverity), default=AlertSeverity.WARNING, nullable=False)

    # Scope
    organization_id: Mapped[Optional[int]] = mapped_column(ForeignKey("organizations.id"), nullable=True, index=True)
    is_global: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Templates
    templates: Mapped[Optional[Dict[str, str]]] = mapped_column(JSON, nullable=True)

    # Status
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_test_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_test_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Metadata
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    organization: Mapped[Optional["Organization"]] = relationship("Organization")
    creator: Mapped["User"] = relationship("User", foreign_keys=[created_by])


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    severity: Mapped[AlertSeverity] = mapped_column(Enum(AlertSeverity), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), default="investigating", nullable=False, index=True)  # investigating, identified, monitoring, resolved, postmortem

    # Timeline
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Ownership
    commander_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    scribe_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    organization_id: Mapped[Optional[int]] = mapped_column(ForeignKey("organizations.id"), nullable=True, index=True)

    # Related alerts
    alert_ids: Mapped[Optional[List[int]]] = mapped_column(JSON, nullable=True)

    # Communication
    communication_channel: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Slack channel, etc.
    status_page_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Postmortem
    postmortem: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    postmortem_published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Metadata
    incident_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    organization: Mapped[Optional["Organization"]] = relationship("Organization")
    commander: Mapped[Optional["User"]] = relationship("User", foreign_keys=[commander_id])
    scribe: Mapped[Optional["User"]] = relationship("User", foreign_keys=[scribe_id])