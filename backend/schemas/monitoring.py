from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, EmailStr
from datetime import datetime
from enum import Enum


class MetricType(str, Enum):
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class AlertStatus(str, Enum):
    FIRING = "firing"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SILENCED = "silenced"


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class LogLevel(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class TraceStatus(str, Enum):
    OK = "ok"
    ERROR = "error"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


# ============= Metrics =============

class MetricCreate(BaseModel):
    name: str
    metric_type: MetricType
    value: float
    labels: Optional[Dict[str, str]] = None
    source: str
    source_instance: Optional[str] = None
    organization_id: Optional[int] = None
    user_id: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


class MetricResponse(BaseModel):
    id: int
    name: str
    metric_type: MetricType
    value: float
    labels: Optional[Dict[str, str]]
    source: str
    source_instance: Optional[str]
    organization_id: Optional[int]
    user_id: Optional[int]
    timestamp: datetime
    recorded_at: datetime
    metadata: Optional[Dict[str, Any]]

    class Config:
        from_attributes = True


class MetricQuery(BaseModel):
    name: str
    source: Optional[str] = None
    organization_id: Optional[int] = None
    user_id: Optional[int] = None
    start_time: datetime
    end_time: datetime
    aggregation: Optional[str] = None  # sum, avg, min, max, count
    interval: Optional[str] = None  # 1m, 5m, 1h, 1d


class MetricAggregation(BaseModel):
    name: str
    count: int
    sum: float
    avg: float
    min: float
    max: float
    percentiles: Optional[Dict[str, float]] = None


# ============= Alert Rules =============

class AlertRuleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    metric_name: str
    condition: str = Field(..., pattern="^(>|<|>=|<=|==|!=)$")
    threshold: float
    evaluation_window: str = "5m"
    label_filters: Optional[Dict[str, str]] = None
    severity: AlertSeverity = AlertSeverity.WARNING
    notification_channels: Optional[List[str]] = None
    notification_template: Optional[str] = None
    cooldown_minutes: int = 15
    organization_id: Optional[int] = None
    applies_to_all_orgs: bool = False


class AlertRuleUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    metric_name: Optional[str] = None
    condition: Optional[str] = Field(None, pattern="^(>|<|>=|<=|==|!=)$")
    threshold: Optional[float] = None
    evaluation_window: Optional[str] = None
    label_filters: Optional[Dict[str, str]] = None
    severity: Optional[AlertSeverity] = None
    notification_channels: Optional[List[str]] = None
    notification_template: Optional[str] = None
    cooldown_minutes: Optional[int] = None
    enabled: Optional[bool] = None


class AlertRuleResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    metric_name: str
    condition: str
    threshold: float
    evaluation_window: str
    label_filters: Optional[Dict[str, str]]
    severity: AlertSeverity
    notification_channels: Optional[List[str]]
    notification_template: Optional[str]
    cooldown_minutes: int
    organization_id: Optional[int]
    applies_to_all_orgs: bool
    enabled: bool
    created_by: int
    created_at: datetime
    updated_at: datetime
    creator_name: Optional[str] = None

    class Config:
        from_attributes = True


# ============= Alerts =============

class AlertResponse(BaseModel):
    id: int
    rule_id: int
    name: str
    description: Optional[str]
    severity: AlertSeverity
    status: AlertStatus
    metric_name: str
    metric_value: float
    threshold: float
    condition: str
    labels: Optional[Dict[str, str]]
    organization_id: Optional[int]
    started_at: datetime
    acknowledged_at: Optional[datetime]
    acknowledged_by: Optional[int]
    resolved_at: Optional[datetime]
    resolved_by: Optional[int]
    silenced_until: Optional[datetime]
    metadata: Optional[Dict[str, Any]]
    rule_name: Optional[str] = None

    class Config:
        from_attributes = True


class AlertAcknowledge(BaseModel):
    acknowledged_by: int


class AlertResolve(BaseModel):
    resolved_by: int


class AlertSilence(BaseModel):
    silenced_until: datetime


# ============= Health Checks =============

class HealthCheckCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    check_type: str = Field(..., pattern="^(http|tcp|database|custom|kafka|redis)$")
    endpoint: Optional[str] = None
    timeout_seconds: int = Field(10, ge=1, le=300)
    interval_seconds: int = Field(60, ge=10, le=3600)
    expected_status: Optional[int] = None
    expected_content: Optional[str] = None
    custom_check: Optional[str] = None
    failure_threshold: int = Field(3, ge=1, le=10)
    success_threshold: int = Field(1, ge=1, le=10)
    organization_id: Optional[int] = None
    is_global: bool = False
    metadata: Optional[Dict[str, Any]] = None


class HealthCheckUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    endpoint: Optional[str] = None
    timeout_seconds: Optional[int] = Field(None, ge=1, le=300)
    interval_seconds: Optional[int] = Field(None, ge=10, le=3600)
    expected_status: Optional[int] = None
    expected_content: Optional[str] = None
    custom_check: Optional[str] = None
    failure_threshold: Optional[int] = Field(None, ge=1, le=10)
    success_threshold: Optional[int] = Field(None, ge=1, le=10)
    enabled: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None


class HealthCheckResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    check_type: str
    endpoint: Optional[str]
    timeout_seconds: int
    interval_seconds: int
    expected_status: Optional[int]
    expected_content: Optional[str]
    custom_check: Optional[str]
    failure_threshold: int
    success_threshold: int
    organization_id: Optional[int]
    is_global: bool
    enabled: bool
    current_status: HealthStatus
    last_check_at: Optional[datetime]
    last_success_at: Optional[datetime]
    last_failure_at: Optional[datetime]
    consecutive_failures: int
    consecutive_successes: int
    metadata: Optional[Dict[str, Any]]
    created_by: int
    created_at: datetime
    updated_at: datetime
    creator_name: Optional[str] = None

    class Config:
        from_attributes = True


class HealthCheckResultResponse(BaseModel):
    id: int
    check_id: int
    status: HealthStatus
    latency_ms: Optional[float]
    response_code: Optional[int]
    response_body: Optional[str]
    error_message: Optional[str]
    checked_at: datetime
    metadata: Optional[Dict[str, Any]]

    class Config:
        from_attributes = True


# ============= Structured Logs =============

class LogQuery(BaseModel):
    level: Optional[LogLevel] = None
    logger_name: Optional[str] = None
    service_name: Optional[str] = None
    organization_id: Optional[int] = None
    user_id: Optional[int] = None
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    search_text: Optional[str] = None
    limit: int = Field(100, le=1000)


class StructuredLogResponse(BaseModel):
    id: int
    timestamp: datetime
    level: LogLevel
    logger_name: str
    service_name: str
    instance_id: Optional[str]
    message: str
    message_template: Optional[str]
    trace_id: Optional[str]
    span_id: Optional[str]
    user_id: Optional[int]
    organization_id: Optional[int]
    session_id: Optional[str]
    request_id: Optional[str]
    fields: Optional[Dict[str, Any]]
    exception_type: Optional[str]
    exception_message: Optional[str]
    stack_trace: Optional[str]


class StructuredLogCreate(BaseModel):
    timestamp: Optional[datetime] = None
    level: LogLevel = LogLevel.INFO
    logger_name: str
    service_name: str
    instance_id: Optional[str] = None
    message: str
    message_template: Optional[str] = None
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    user_id: Optional[int] = None
    organization_id: Optional[int] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    fields: Optional[Dict[str, Any]] = None
    exception_type: Optional[str] = None
    exception_message: Optional[str] = None
    stack_trace: Optional[str] = None

    class Config:
        from_attributes = True


# ============= Traces & Spans =============

class TraceCreate(BaseModel):
    trace_id: str
    parent_span_id: Optional[str] = None
    service_name: str
    operation_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    status: TraceStatus = TraceStatus.OK
    error_message: Optional[str] = None
    user_id: Optional[int] = None
    organization_id: Optional[int] = None
    request_id: Optional[str] = None
    tags: Optional[Dict[str, str]] = None
    metadata: Optional[Dict[str, Any]] = None


class TraceResponse(BaseModel):
    id: int
    trace_id: str
    parent_span_id: Optional[str]
    service_name: str
    operation_name: str
    start_time: datetime
    end_time: Optional[datetime]
    duration_ms: Optional[float]
    status: TraceStatus
    error_message: Optional[str]
    user_id: Optional[int]
    organization_id: Optional[int]
    request_id: Optional[str]
    tags: Optional[Dict[str, str]]
    metadata: Optional[Dict[str, Any]]

    class Config:
        from_attributes = True


class SpanCreate(BaseModel):
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    service_name: str
    operation_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    status: TraceStatus = TraceStatus.OK
    error_message: Optional[str] = None
    user_id: Optional[int] = None
    organization_id: Optional[int] = None
    tags: Optional[Dict[str, str]] = None
    metadata: Optional[Dict[str, Any]] = None


class SpanResponse(BaseModel):
    id: int
    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    service_name: str
    operation_name: str
    start_time: datetime
    end_time: Optional[datetime]
    duration_ms: Optional[float]
    status: TraceStatus
    error_message: Optional[str]
    user_id: Optional[int]
    organization_id: Optional[int]
    tags: Optional[Dict[str, str]]
    metadata: Optional[Dict[str, Any]]

    class Config:
        from_attributes = True


# ============= Dashboards =============

class DashboardPanelCreate(BaseModel):
    title: str
    panel_type: str = Field(..., pattern="^(graph|stat|table|heatmap|logs|traces)$")
    visualization: Dict[str, Any]
    query: str
    metric_name: Optional[str] = None
    time_range: str = "1h"
    x: int = 0
    y: int = 0
    width: int = 6
    height: int = 4
    options: Optional[Dict[str, Any]] = None


class DashboardPanelUpdate(BaseModel):
    title: Optional[str] = None
    panel_type: Optional[str] = None
    visualization: Optional[Dict[str, Any]] = None
    query: Optional[str] = None
    metric_name: Optional[str] = None
    time_range: Optional[str] = None
    x: Optional[int] = None
    y: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    options: Optional[Dict[str, Any]] = None


class DashboardPanelResponse(BaseModel):
    id: int
    dashboard_id: int
    title: str
    panel_type: str
    visualization: Dict[str, Any]
    query: str
    metric_name: Optional[str]
    time_range: str
    x: int
    y: int
    width: int
    height: int
    options: Optional[Dict[str, Any]]

    class Config:
        from_attributes = True


class DashboardCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    slug: str = Field(..., min_length=1, max_length=100, pattern="^[a-z0-9-]+$")
    layout: Dict[str, Any] = Field(default_factory=dict)
    organization_id: Optional[int] = None
    is_global: bool = False
    is_default: bool = False
    is_public: bool = False
    allowed_roles: Optional[List[str]] = None
    allowed_users: Optional[List[int]] = None
    tags: Optional[List[str]] = None


class DashboardUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    layout: Optional[Dict[str, Any]] = None
    is_global: Optional[bool] = None
    is_default: Optional[bool] = None
    is_public: Optional[bool] = None
    allowed_roles: Optional[List[str]] = None
    allowed_users: Optional[List[int]] = None
    tags: Optional[List[str]] = None


class DashboardResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    slug: str
    layout: Dict[str, Any]
    organization_id: Optional[int]
    is_global: bool
    is_default: bool
    is_public: bool
    allowed_roles: Optional[List[str]]
    allowed_users: Optional[List[int]]
    tags: Optional[List[str]]
    created_by: int
    created_at: datetime
    updated_at: datetime
    creator_name: Optional[str] = None
    panels: List[DashboardPanelResponse] = []

    class Config:
        from_attributes = True


# ============= Notification Channels =============

class NotificationChannelCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    channel_type: str = Field(..., pattern="^(email|slack|webhook|pagerduty|sms)$")
    config: Dict[str, Any]
    default_severity: AlertSeverity = AlertSeverity.WARNING
    organization_id: Optional[int] = None
    is_global: bool = False
    templates: Optional[Dict[str, str]] = None


class NotificationChannelUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    config: Optional[Dict[str, Any]] = None
    default_severity: Optional[AlertSeverity] = None
    templates: Optional[Dict[str, str]] = None
    enabled: Optional[bool] = None


class NotificationChannelResponse(BaseModel):
    id: int
    name: str
    channel_type: str
    config: Dict[str, Any]
    default_severity: AlertSeverity
    organization_id: Optional[int]
    is_global: bool
    templates: Optional[Dict[str, str]]
    enabled: bool
    last_test_at: Optional[datetime]
    last_test_status: Optional[str]
    created_by: int
    created_at: datetime
    updated_at: datetime
    creator_name: Optional[str] = None

    class Config:
        from_attributes = True


class NotificationTest(BaseModel):
    channel_id: int
    test_message: str = "Test notification from CareerIntel AI"


# ============= Incidents =============

class IncidentCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    severity: AlertSeverity = AlertSeverity.WARNING
    organization_id: Optional[int] = None
    commander_id: Optional[int] = None
    scribe_id: Optional[int] = None
    alert_ids: Optional[List[int]] = None
    communication_channel: Optional[str] = None


class IncidentUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    severity: Optional[AlertSeverity] = None
    status: Optional[str] = None
    commander_id: Optional[int] = None
    scribe_id: Optional[int] = None
    communication_channel: Optional[str] = None
    status_page_url: Optional[str] = None
    postmortem: Optional[str] = None


class IncidentResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    severity: AlertSeverity
    status: str
    started_at: datetime
    acknowledged_at: Optional[datetime]
    resolved_at: Optional[datetime]
    closed_at: Optional[datetime]
    commander_id: Optional[int]
    scribe_id: Optional[int]
    organization_id: Optional[int]
    alert_ids: Optional[List[int]]
    communication_channel: Optional[str]
    status_page_url: Optional[str]
    postmortem: Optional[str]
    postmortem_published_at: Optional[datetime]
    metadata: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime
    commander_name: Optional[str] = None
    scribe_name: Optional[str] = None

    class Config:
        from_attributes = True


class IncidentTimelineEvent(BaseModel):
    timestamp: datetime
    event_type: str
    description: str
    user_id: Optional[int] = None
    user_name: Optional[str] = None


# ============= Agent Execution History =============

class AgentExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class AgentExecutionCreate(BaseModel):
    execution_id: str
    trace_id: Optional[str] = None
    agent_name: str
    agent_type: str
    agent_version: Optional[str] = None
    parent_execution_id: Optional[str] = None
    workflow_id: Optional[str] = None
    workflow_name: Optional[str] = None
    phase: Optional[str] = None
    input_data: Optional[Dict[str, Any]] = None
    user_id: Optional[int] = None
    organization_id: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None
    tags: Optional[Dict[str, str]] = None


class AgentExecutionUpdate(BaseModel):
    status: Optional[AgentExecutionStatus] = None
    output_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    ended_at: Optional[datetime] = None
    duration_ms: Optional[float] = None
    cpu_time_ms: Optional[float] = None
    memory_mb: Optional[float] = None
    llm_calls: Optional[int] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    estimated_cost_usd: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


class AgentExecutionResponse(BaseModel):
    id: int
    execution_id: str
    trace_id: Optional[str]
    agent_name: str
    agent_type: str
    agent_version: Optional[str]
    parent_execution_id: Optional[str]
    workflow_id: Optional[str]
    workflow_name: Optional[str]
    phase: Optional[str]
    input_data: Optional[Dict[str, Any]]
    output_data: Optional[Dict[str, Any]]
    error_message: Optional[str]
    status: AgentExecutionStatus
    started_at: datetime
    ended_at: Optional[datetime]
    duration_ms: Optional[float]
    cpu_time_ms: Optional[float]
    memory_mb: Optional[float]
    llm_calls: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost_usd: Optional[float]
    user_id: Optional[int]
    organization_id: Optional[int]
    metadata: Optional[Dict[str, Any]]
    tags: Optional[Dict[str, str]]

    class Config:
        from_attributes = True


class AgentExecutionQuery(BaseModel):
    agent_name: Optional[str] = None
    agent_type: Optional[str] = None
    workflow_id: Optional[str] = None
    trace_id: Optional[str] = None
    status: Optional[AgentExecutionStatus] = None
    user_id: Optional[int] = None
    organization_id: Optional[int] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    limit: int = Field(100, le=500)


# ============= Tool Execution History =============

class ToolExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"


class ToolExecutionCreate(BaseModel):
    execution_id: str
    trace_id: Optional[str] = None
    agent_execution_id: Optional[str] = None
    tool_name: str
    tool_type: str
    tool_version: Optional[str] = None
    input_data: Optional[Dict[str, Any]] = None
    user_id: Optional[int] = None
    organization_id: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


class ToolExecutionUpdate(BaseModel):
    status: Optional[ToolExecutionStatus] = None
    output_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    ended_at: Optional[datetime] = None
    duration_ms: Optional[float] = None
    retries: Optional[int] = None
    rate_limit_remaining: Optional[int] = None
    estimated_cost_usd: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


class ToolExecutionResponse(BaseModel):
    id: int
    execution_id: str
    trace_id: Optional[str]
    agent_execution_id: Optional[str]
    tool_name: str
    tool_type: str
    tool_version: Optional[str]
    input_data: Optional[Dict[str, Any]]
    output_data: Optional[Dict[str, Any]]
    error_message: Optional[str]
    status: ToolExecutionStatus
    started_at: datetime
    ended_at: Optional[datetime]
    duration_ms: Optional[float]
    retries: int
    rate_limit_remaining: Optional[int]
    estimated_cost_usd: Optional[float]
    user_id: Optional[int]
    organization_id: Optional[int]
    metadata: Optional[Dict[str, Any]]

    class Config:
        from_attributes = True


class ToolExecutionQuery(BaseModel):
    tool_name: Optional[str] = None
    tool_type: Optional[str] = None
    trace_id: Optional[str] = None
    agent_execution_id: Optional[str] = None
    status: Optional[ToolExecutionStatus] = None
    user_id: Optional[int] = None
    organization_id: Optional[int] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    limit: int = Field(100, le=500)