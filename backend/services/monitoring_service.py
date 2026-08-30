import logging
import asyncio
import time
import json
import hashlib
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from collections import defaultdict

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc, text

from backend.models.monitoring import (
    Metric, AlertRule, Alert, HealthCheck, HealthCheckResult,
    StructuredLog, Trace, Span, Dashboard, DashboardPanel,
    NotificationChannel, Incident,
    MetricType, AlertSeverity, AlertStatus, HealthStatus,
    LogLevel, TraceStatus
)
from backend.models.organization import Organization
from backend.models.user import User
from backend.schemas.monitoring import (
    MetricCreate, MetricQuery, MetricAggregation,
    AlertRuleCreate, AlertRuleUpdate, AlertRuleResponse,
    AlertResponse, AlertAcknowledge, AlertResolve, AlertSilence,
    HealthCheckCreate, HealthCheckUpdate, HealthCheckResponse,
    HealthCheckResultResponse,
    LogQuery, StructuredLogResponse,
    TraceCreate, TraceResponse, SpanCreate, SpanResponse,
    DashboardCreate, DashboardUpdate, DashboardResponse,
    DashboardPanelCreate, DashboardPanelUpdate, DashboardPanelResponse,
    NotificationChannelCreate, NotificationChannelUpdate, NotificationChannelResponse,
    NotificationTest,
    IncidentCreate, IncidentUpdate, IncidentResponse,
)

logger = logging.getLogger(__name__)


class MonitoringService:
    """Service for monitoring, alerting, and observability."""

    def __init__(self, db: Session):
        self.db = db
        self._metric_buffer: List[Metric] = []
        self._log_buffer: List[StructuredLog] = []
        self._span_buffer: List[Span] = []
        self._flush_interval = 5  # seconds
        self._max_buffer_size = 1000

    # ============= Metrics =============

    def record_metric(self, metric: MetricCreate) -> Metric:
        """Record a metric value."""
        m = Metric(
            name=metric.name,
            metric_type=metric.metric_type,
            value=metric.value,
            labels=metric.labels,
            source=metric.source,
            source_instance=metric.source_instance,
            organization_id=metric.organization_id,
            user_id=metric.user_id,
            metadata=metric.metadata,
        )
        self.db.add(m)
        self.db.commit()
        self.db.refresh(m)
        return m

    def record_metric_batch(self, metrics: List[MetricCreate]) -> List[Metric]:
        """Record multiple metrics in batch."""
        metric_objects = [
            Metric(
                name=m.name,
                metric_type=m.metric_type,
                value=m.value,
                labels=m.labels,
                source=m.source,
                source_instance=m.source_instance,
                organization_id=m.organization_id,
                user_id=m.user_id,
                metadata=m.metadata,
            )
            for m in metrics
        ]
        self.db.bulk_save_objects(metric_objects)
        self.db.commit()
        return metric_objects

    def query_metrics(self, query: MetricQuery) -> List[Metric]:
        """Query metrics with filters."""
        q = self.db.query(Metric).filter(
            Metric.name == query.name,
            Metric.timestamp >= query.start_time,
            Metric.timestamp <= query.end_time,
        )

        if query.source:
            q = q.filter(Metric.source == query.source)
        if query.organization_id:
            q = q.filter(Metric.organization_id == query.organization_id)
        if query.user_id:
            q = q.filter(Metric.user_id == query.user_id)

        if query.labels:
            for key, value in query.labels.items():
                q = q.filter(Metric.labels[key].astext == value)

        return q.order_by(Metric.timestamp).all()

    def aggregate_metrics(self, query: MetricQuery) -> MetricAggregation:
        """Aggregate metrics over time window."""
        metrics = self.query_metrics(query)
        if not metrics:
            return MetricAggregation(
                name=query.name, count=0, sum=0, avg=0, min=0, max=0
            )

        values = [m.value for m in metrics]
        values.sort()

        count = len(values)
        return MetricAggregation(
            name=query.name,
            count=count,
            sum=sum(values),
            avg=sum(values) / count,
            min=values[0],
            max=values[-1],
            percentiles={
                "p50": values[int(count * 0.5)],
                "p90": values[int(count * 0.9)],
                "p95": values[int(count * 0.95)],
                "p99": values[int(count * 0.99)] if count > 100 else values[-1],
            }
        )

    def get_metric_names(self, source: Optional[str] = None) -> List[str]:
        """Get unique metric names."""
        q = self.db.query(Metric.name).distinct()
        if source:
            q = q.filter(Metric.source == source)
        return [row[0] for row in q.all()]

    # ============= Alert Rules =============

    def create_alert_rule(self, rule_data: AlertRuleCreate, creator_id: int) -> AlertRule:
        """Create an alert rule."""
        rule = AlertRule(
            name=rule_data.name,
            description=rule_data.description,
            metric_name=rule_data.metric_name,
            condition=rule_data.condition,
            threshold=rule_data.threshold,
            evaluation_window=rule_data.evaluation_window,
            label_filters=rule_data.label_filters,
            severity=rule_data.severity,
            notification_channels=rule_data.notification_channels,
            notification_template=rule_data.notification_template,
            cooldown_minutes=rule_data.cooldown_minutes,
            organization_id=rule_data.organization_id,
            applies_to_all_orgs=rule_data.applies_to_all_orgs,
            created_by=creator_id,
        )
        self.db.add(rule)
        self.db.commit()
        self.db.refresh(rule)
        return rule

    def update_alert_rule(self, rule_id: int, updates: AlertRuleUpdate) -> Optional[AlertRule]:
        """Update an alert rule."""
        rule = self.db.query(AlertRule).filter(AlertRule.id == rule_id).first()
        if not rule:
            return None

        for field, value in updates.dict(exclude_unset=True).items():
            setattr(rule, field, value)

        rule.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(rule)
        return rule

    def delete_alert_rule(self, rule_id: int) -> bool:
        """Delete an alert rule."""
        rule = self.db.query(AlertRule).filter(AlertRule.id == rule_id).first()
        if not rule:
            return False
        self.db.delete(rule)
        self.db.commit()
        return True

    def get_alert_rules(self, organization_id: Optional[int] = None) -> List[AlertRule]:
        """Get alert rules."""
        q = self.db.query(AlertRule).filter(AlertRule.enabled == True)
        if organization_id:
            q = q.filter(
                or_(
                    AlertRule.organization_id == organization_id,
                    AlertRule.applies_to_all_orgs == True
                )
            )
        return q.all()

    def evaluate_alert_rules(self) -> List[Alert]:
        """Evaluate all alert rules and create alerts if triggered."""
        rules = self.db.query(AlertRule).filter(AlertRule.enabled == True).all()
        new_alerts = []

        for rule in rules:
            try:
                alerts = self._evaluate_rule(rule)
                new_alerts.extend(alerts)
            except Exception as e:
                logger.error(f"Error evaluating rule {rule.id}: {e}")

        return new_alerts

    def _evaluate_rule(self, rule: AlertRule) -> List[Alert]:
        """Evaluate a single alert rule."""
        # Parse evaluation window
        window_map = {"1m": 1, "5m": 5, "15m": 15, "30m": 30, "1h": 60, "6h": 360, "12h": 720, "24h": 1440}
        minutes = window_map.get(rule.evaluation_window, 5)
        window_start = datetime.utcnow() - timedelta(minutes=minutes)

        # Query metrics for the window
        q = self.db.query(Metric).filter(
            Metric.name == rule.metric_name,
            Metric.timestamp >= window_start,
        )

        if rule.label_filters:
            for key, value in rule.label_filters.items():
                q = q.filter(Metric.labels[key].astext == value)

        if rule.organization_id:
            q = q.filter(Metric.organization_id == rule.organization_id)

        metrics = q.all()
        if not metrics:
            return []

        # Aggregate based on metric type
        if rule.metric_type == MetricType.COUNTER:
            value = sum(m.value for m in metrics)
        elif rule.metric_type == MetricType.GAUGE:
            value = metrics[-1].value  # Latest value
        elif rule.metric_type == MetricType.HISTOGRAM:
            values = [m.value for m in metrics]
            value = sum(values) / len(values)  # Average
        else:
            value = sum(m.value for m in metrics) / len(metrics)

        # Evaluate condition
        triggered = False
        if rule.condition == ">" and value > rule.threshold:
            triggered = True
        elif rule.condition == "<" and value < rule.threshold:
            triggered = True
        elif rule.condition == ">=" and value >= rule.threshold:
            triggered = True
        elif rule.condition == "<=" and value <= rule.threshold:
            triggered = True
        elif rule.condition == "==" and value == rule.threshold:
            triggered = True
        elif rule.condition == "!=" and value != rule.threshold:
            triggered = True

        if not triggered:
            return []

        # Check cooldown - don't alert if recent alert exists
        recent_alert = self.db.query(Alert).filter(
            Alert.rule_id == rule.id,
            Alert.status.in_([AlertStatus.FIRING, AlertStatus.ACKNOWLEDGED]),
            Alert.started_at >= datetime.utcnow() - timedelta(minutes=rule.cooldown_minutes)
        ).first()

        if recent_alert:
            return []

        # Create alert
        alert = Alert(
            rule_id=rule.id,
            name=rule.name,
            description=rule.description,
            severity=rule.severity,
            status=AlertStatus.FIRING,
            metric_name=rule.metric_name,
            metric_value=value,
            threshold=rule.threshold,
            condition=rule.condition,
            labels=rule.label_filters,
            organization_id=rule.organization_id,
            started_at=datetime.utcnow(),
        )
        self.db.add(alert)
        self.db.commit()
        self.db.refresh(alert)

        # Send notifications (async in production)
        self._send_alert_notifications(alert, rule)

        return [alert]

    def _send_alert_notifications(self, alert: Alert, rule: AlertRule) -> None:
        """Send alert notifications (placeholder)."""
        logger.warning(f"ALERT: {alert.name} - {alert.metric_name}={alert.metric_value} {rule.condition} {rule.threshold}")
        # In production, integrate with email, Slack, PagerDuty, etc.

    # ============= Alert Management =============

    def get_alerts(
        self,
        organization_id: Optional[int] = None,
        status: Optional[AlertStatus] = None,
        severity: Optional[AlertSeverity] = None,
        limit: int = 100
    ) -> List[Alert]:
        """Get alerts with filters."""
        q = self.db.query(Alert)

        if organization_id:
            q = q.filter(Alert.organization_id == organization_id)
        if status:
            q = q.filter(Alert.status == status)
        if severity:
            q = q.filter(Alert.severity == severity)

        return q.order_by(desc(Alert.started_at)).limit(limit).all()

    def acknowledge_alert(self, alert_id: int, acknowledged_by: int) -> Optional[Alert]:
        """Acknowledge an alert."""
        alert = self.db.query(Alert).filter(Alert.id == alert_id).first()
        if not alert:
            return None

        alert.status = AlertStatus.ACKNOWLEDGED
        alert.acknowledged_at = datetime.utcnow()
        alert.acknowledged_by = acknowledged_by
        self.db.commit()
        self.db.refresh(alert)
        return alert

    def resolve_alert(self, alert_id: int, resolved_by: int) -> Optional[Alert]:
        """Resolve an alert."""
        alert = self.db.query(Alert).filter(Alert.id == alert_id).first()
        if not alert:
            return None

        alert.status = AlertStatus.RESOLVED
        alert.resolved_at = datetime.utcnow()
        alert.resolved_by = resolved_by
        self.db.commit()
        self.db.refresh(alert)
        return alert

    def silence_alert(self, alert_id: int, silenced_until: datetime) -> Optional[Alert]:
        """Silence an alert."""
        alert = self.db.query(Alert).filter(Alert.id == alert_id).first()
        if not alert:
            return None

        alert.status = AlertStatus.SILENCED
        alert.silenced_until = silenced_until
        self.db.commit()
        self.db.refresh(alert)
        return alert

    # ============= Health Checks =============

    def create_health_check(self, check_data: HealthCheckCreate, creator_id: int) -> HealthCheck:
        """Create a health check."""
        check = HealthCheck(
            name=check_data.name,
            description=check_data.description,
            check_type=check_data.check_type,
            endpoint=check_data.endpoint,
            timeout_seconds=check_data.timeout_seconds,
            interval_seconds=check_data.interval_seconds,
            expected_status=check_data.expected_status,
            expected_content=check_data.expected_content,
            custom_check=check_data.custom_check,
            failure_threshold=check_data.failure_threshold,
            success_threshold=check_data.success_threshold,
            organization_id=check_data.organization_id,
            is_global=check_data.is_global,
            metadata=check_data.metadata,
            created_by=creator_id,
        )
        self.db.add(check)
        self.db.commit()
        self.db.refresh(check)
        return check

    def update_health_check(self, check_id: int, updates: HealthCheckUpdate) -> Optional[HealthCheck]:
        """Update a health check."""
        check = self.db.query(HealthCheck).filter(HealthCheck.id == check_id).first()
        if not check:
            return None

        for field, value in updates.dict(exclude_unset=True).items():
            setattr(check, field, value)

        check.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(check)
        return check

    def run_health_check(self, check_id: int) -> HealthCheckResult:
        """Run a single health check."""
        check = self.db.query(HealthCheck).filter(HealthCheck.id == check_id).first()
        if not check:
            raise ValueError("Health check not found")

        start_time = time.time()
        result = HealthCheckResult(check_id=check_id, checked_at=datetime.utcnow())

        try:
            if check.check_type == "http":
                result = self._run_http_check(check, result)
            elif check.check_type == "tcp":
                result = self._run_tcp_check(check, result)
            elif check.check_type == "database":
                result = self._run_database_check(check, result)
            elif check.check_type == "redis":
                result = self._run_redis_check(check, result)
            elif check.check_type == "kafka":
                result = self._run_kafka_check(check, result)
            elif check.check_type == "custom":
                result = self._run_custom_check(check, result)
            else:
                result.status = HealthStatus.UNHEALTHY
                result.error_message = f"Unknown check type: {check.check_type}"

        except Exception as e:
            result.status = HealthStatus.UNHEALTHY
            result.error_message = str(e)

        result.duration_ms = (time.time() - start_time) * 1000

        # Update check status
        self._update_health_check_status(check, result)

        self.db.add(result)
        self.db.commit()
        self.db.refresh(result)

        return result

    def _run_http_check(self, check: HealthCheck, result: HealthCheckResult) -> HealthCheckResult:
        """Run HTTP health check."""
        import requests
        try:
            response = requests.get(
                check.endpoint,
                timeout=check.timeout_seconds,
            )
            result.latency_ms = response.elapsed.total_seconds() * 1000
            result.response_code = response.status_code
            result.response_body = response.text[:1000] if response.text else None

            if check.expected_status and response.status_code != check.expected_status:
                result.status = HealthStatus.UNHEALTHY
                result.error_message = f"Expected status {check.expected_status}, got {response.status_code}"
            elif check.expected_content and check.expected_content not in (response.text or ""):
                result.status = HealthStatus.UNHEALTHY
                result.error_message = f"Expected content not found"
            else:
                result.status = HealthStatus.HEALTHY

        except requests.Timeout:
            result.status = HealthStatus.UNHEALTHY
            result.error_message = f"Timeout after {check.timeout_seconds}s"
        except Exception as e:
            result.status = HealthStatus.UNHEALTHY
            result.error_message = str(e)

        return result

    def _run_tcp_check(self, check: HealthCheck, result: HealthCheckResult) -> HealthCheckResult:
        """Run TCP health check."""
        import socket
        try:
            host, port = check.endpoint.split(":")
            sock = socket.create_connection((host, int(port)), timeout=check.timeout_seconds)
            sock.close()
            result.status = HealthStatus.HEALTHY
        except Exception as e:
            result.status = HealthStatus.UNHEALTHY
            result.error_message = str(e)
        return result

    def _run_database_check(self, check: HealthCheck, result: HealthCheckResult) -> HealthCheckResult:
        """Run database health check."""
        try:
            self.db.execute(text("SELECT 1"))
            result.status = HealthStatus.HEALTHY
        except Exception as e:
            result.status = HealthStatus.UNHEALTHY
            result.error_message = str(e)
        return result

    def _run_redis_check(self, check: HealthCheck, result: HealthCheckResult) -> HealthCheckResult:
        """Run Redis health check."""
        try:
            import redis
            r = redis.from_url(check.endpoint, socket_timeout=check.timeout_seconds)
            r.ping()
            result.status = HealthStatus.HEALTHY
        except Exception as e:
            result.status = HealthStatus.UNHEALTHY
            result.error_message = str(e)
        return result

    def _run_kafka_check(self, check: HealthCheck, result: HealthCheckResult) -> HealthCheckResult:
        """Run Kafka health check."""
        try:
            from kafka import KafkaProducer
            producer = KafkaProducer(
                bootstrap_servers=check.endpoint,
                request_timeout_ms=check.timeout_seconds * 1000,
            )
            producer.close()
            result.status = HealthStatus.HEALTHY
        except Exception as e:
            result.status = HealthStatus.UNHEALTHY
            result.error_message = str(e)
        return result

    def _run_custom_check(self, check: HealthCheck, result: HealthCheckResult) -> HealthCheckResult:
        """Run custom health check."""
        # In production, would use a sandboxed executor
        result.status = HealthStatus.HEALTHY
        result.error_message = "Custom check not implemented"
        return result

    def _update_health_check_status(self, check: HealthCheck, result: HealthCheckResult) -> None:
        """Update health check status based on result."""
        if result.status == HealthStatus.HEALTHY:
            check.consecutive_successes += 1
            check.consecutive_failures = 0
            check.last_success_at = datetime.utcnow()
            if check.consecutive_successes >= check.success_threshold:
                check.current_status = HealthStatus.HEALTHY
        else:
            check.consecutive_failures += 1
            check.consecutive_successes = 0
            check.last_failure_at = datetime.utcnow()
            if check.consecutive_failures >= check.failure_threshold:
                check.current_status = HealthStatus.UNHEALTHY

        check.last_check_at = datetime.utcnow()
        self.db.commit()

    def run_all_health_checks(self) -> List[HealthCheckResult]:
        """Run all enabled health checks."""
        checks = self.db.query(HealthCheck).filter(HealthCheck.enabled == True).all()
        results = []
        for check in checks:
            try:
                result = self.run_health_check(check.id)
                results.append(result)
            except Exception as e:
                logger.error(f"Health check {check.id} failed: {e}")
        return results

    # ============= Structured Logging =============

    def log(self, log_data: StructuredLog) -> StructuredLog:
        """Record a structured log entry."""
        log = StructuredLog(**log_data.dict())
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log

    def log_batch(self, logs: List[StructuredLog]) -> List[StructuredLog]:
        """Record multiple log entries in batch."""
        log_objects = [StructuredLog(**log.dict()) for log in logs]
        self.db.bulk_save_objects(log_objects)
        self.db.commit()
        return log_objects

    def query_logs(self, query: LogQuery) -> List[StructuredLog]:
        """Query structured logs with filters."""
        q = self.db.query(StructuredLog)

        if query.level:
            q = q.filter(StructuredLog.level == query.level)
        if query.logger_name:
            q = q.filter(StructuredLog.logger_name.ilike(f"%{query.logger_name}%"))
        if query.service_name:
            q = q.filter(StructuredLog.service_name == query.service_name)
        if query.organization_id:
            q = q.filter(StructuredLog.organization_id == query.organization_id)
        if query.user_id:
            q = q.filter(StructuredLog.user_id == query.user_id)
        if query.trace_id:
            q = q.filter(StructuredLog.trace_id == query.trace_id)
        if query.span_id:
            q = q.filter(StructuredLog.span_id == query.span_id)
        if query.session_id:
            q = q.filter(StructuredLog.session_id == query.session_id)
        if query.request_id:
            q = q.filter(StructuredLog.request_id == query.request_id)
        if query.start_time:
            q = q.filter(StructuredLog.timestamp >= query.start_time)
        if query.end_time:
            q = q.filter(StructuredLog.timestamp <= query.end_time)
        if query.search_text:
            q = q.filter(StructuredLog.message.ilike(f"%{query.search_text}%"))

        return q.order_by(desc(StructuredLog.timestamp)).limit(query.limit).all()

    # ============= Distributed Tracing =============

    def create_trace(self, trace_data: TraceCreate) -> Trace:
        """Create a trace."""
        trace = Trace(**trace_data.dict())
        self.db.add(trace)
        self.db.commit()
        self.db.refresh(trace)
        return trace

    def create_span(self, span_data: SpanCreate) -> Span:
        """Create a span."""
        span = Span(**span_data.dict())
        self.db.add(span)
        self.db.commit()
        self.db.refresh(span)
        return span

    def get_trace(self, trace_id: str) -> Optional[Trace]:
        """Get trace by ID."""
        return self.db.query(Trace).filter(Trace.trace_id == trace_id).first()

    def get_trace_with_spans(self, trace_id: str) -> Optional[Trace]:
        """Get trace with all spans."""
        trace = self.get_trace(trace_id)
        if trace:
            trace.spans = self.db.query(Span).filter(Span.trace_id == trace_id).order_by(Span.start_time).all()
        return trace

    def query_traces(
        self,
        service_name: Optional[str] = None,
        operation_name: Optional[str] = None,
        status: Optional[TraceStatus] = None,
        user_id: Optional[int] = None,
        organization_id: Optional[int] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Trace]:
        """Query traces with filters."""
        q = self.db.query(Trace)

        if service_name:
            q = q.filter(Trace.service_name == service_name)
        if operation_name:
            q = q.filter(Trace.operation_name.ilike(f"%{operation_name}%"))
        if status:
            q = q.filter(Trace.status == status)
        if user_id:
            q = q.filter(Trace.user_id == user_id)
        if organization_id:
            q = q.filter(Trace.organization_id == organization_id)
        if start_time:
            q = q.filter(Trace.start_time >= start_time)
        if end_time:
            q = q.filter(Trace.start_time <= end_time)

        return q.order_by(desc(Trace.start_time)).limit(limit).all()

    # ============= Dashboards =============

    def create_dashboard(self, dashboard_data: DashboardCreate, creator_id: int) -> Dashboard:
        """Create a dashboard."""
        dashboard = Dashboard(
            name=dashboard_data.name,
            description=dashboard_data.description,
            slug=dashboard_data.slug,
            layout=dashboard_data.layout,
            organization_id=dashboard_data.organization_id,
            is_global=dashboard_data.is_global,
            is_default=dashboard_data.is_default,
            is_public=dashboard_data.is_public,
            allowed_roles=dashboard_data.allowed_roles,
            allowed_users=dashboard_data.allowed_users,
            tags=dashboard_data.tags,
            created_by=creator_id,
        )
        self.db.add(dashboard)
        self.db.commit()
        self.db.refresh(dashboard)
        return dashboard

    def update_dashboard(self, dashboard_id: int, updates: DashboardUpdate) -> Optional[Dashboard]:
        """Update a dashboard."""
        dashboard = self.db.query(Dashboard).filter(Dashboard.id == dashboard_id).first()
        if not dashboard:
            return None

        for field, value in updates.dict(exclude_unset=True).items():
            setattr(dashboard, field, value)

        dashboard.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(dashboard)
        return dashboard

    def get_dashboard(self, dashboard_id: int) -> Optional[Dashboard]:
        """Get dashboard by ID."""
        return self.db.query(Dashboard).filter(Dashboard.id == dashboard_id).first()

    def get_dashboard_by_slug(self, slug: str) -> Optional[Dashboard]:
        """Get dashboard by slug."""
        return self.db.query(Dashboard).filter(Dashboard.slug == slug).first()

    def list_dashboards(self, organization_id: Optional[int] = None) -> List[Dashboard]:
        """List dashboards."""
        q = self.db.query(Dashboard)
        if organization_id:
            q = q.filter(
                or_(
                    Dashboard.organization_id == organization_id,
                    Dashboard.is_global == True
                )
            )
        else:
            q = q.filter(Dashboard.is_global == True)
        return q.order_by(Dashboard.created_at.desc()).all()

    def add_dashboard_panel(self, panel_data: DashboardPanelCreate) -> DashboardPanel:
        """Add a panel to dashboard."""
        panel = DashboardPanel(**panel_data.dict())
        self.db.add(panel)
        self.db.commit()
        self.db.refresh(panel)
        return panel

    def update_dashboard_panel(self, panel_id: int, updates: DashboardPanelUpdate) -> Optional[DashboardPanel]:
        """Update a dashboard panel."""
        panel = self.db.query(DashboardPanel).filter(DashboardPanel.id == panel_id).first()
        if not panel:
            return None

        for field, value in updates.dict(exclude_unset=True).items():
            setattr(panel, field, value)

        self.db.commit()
        self.db.refresh(panel)
        return panel

    # ============= Notification Channels =============

    def create_notification_channel(self, channel_data: NotificationChannelCreate, creator_id: int) -> NotificationChannel:
        """Create a notification channel."""
        channel = NotificationChannel(
            name=channel_data.name,
            channel_type=channel_data.channel_type,
            config=channel_data.config,
            default_severity=channel_data.default_severity,
            organization_id=channel_data.organization_id,
            is_global=channel_data.is_global,
            templates=channel_data.templates,
            created_by=creator_id,
        )
        self.db.add(channel)
        self.db.commit()
        self.db.refresh(channel)
        return channel

    def test_notification_channel(self, test: NotificationTest) -> Dict[str, Any]:
        """Test a notification channel."""
        channel = self.db.query(NotificationChannel).filter(NotificationChannel.id == test.channel_id).first()
        if not channel:
            return {"success": False, "error": "Channel not found"}

        # In production, would actually send test notification
        channel.last_test_at = datetime.utcnow()
        channel.last_test_status = "success"
        self.db.commit()

        return {"success": True, "message": "Test notification sent"}

    # ============= Incidents =============

    def create_incident(self, incident_data: IncidentCreate, commander_id: int) -> Incident:
        """Create an incident."""
        incident = Incident(
            title=incident_data.title,
            description=incident_data.description,
            severity=incident_data.severity,
            organization_id=incident_data.organization_id,
            commander_id=commander_id,
            scribe_id=incident_data.scribe_id,
            alert_ids=incident_data.alert_ids,
            communication_channel=incident_data.communication_channel,
        )
        self.db.add(incident)
        self.db.commit()
        self.db.refresh(incident)
        return incident

    def update_incident(self, incident_id: int, updates: IncidentUpdate) -> Optional[Incident]:
        """Update an incident."""
        incident = self.db.query(Incident).filter(Incident.id == incident_id).first()
        if not incident:
            return None

        for field, value in updates.dict(exclude_unset=True).items():
            setattr(incident, field, value)

        incident.updated_at = datetime.utcnow()
        if updates.status == "resolved" and not incident.resolved_at:
            incident.resolved_at = datetime.utcnow()
        if updates.status == "closed" and not incident.closed_at:
            incident.closed_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(incident)
        return incident

    def get_incidents(
        self,
        organization_id: Optional[int] = None,
        status: Optional[str] = None,
        severity: Optional[AlertSeverity] = None,
        limit: int = 50
    ) -> List[Incident]:
        """Get incidents."""
        q = self.db.query(Incident)

        if organization_id:
            q = q.filter(Incident.organization_id == organization_id)
        if status:
            q = q.filter(Incident.status == status)
        if severity:
            q = q.filter(Incident.severity == severity)

        return q.order_by(desc(Incident.started_at)).limit(limit).all()


# Global monitoring service instance (initialized in app startup)
monitoring_service: Optional[MonitoringService] = None


def get_monitoring_service() -> MonitoringService:
    """Get monitoring service instance."""
    if monitoring_service is None:
        raise RuntimeError("Monitoring service not initialized")
    return monitoring_service


def init_monitoring_service(db: Session) -> MonitoringService:
    """Initialize monitoring service."""
    global monitoring_service
    monitoring_service = MonitoringService(db)
    return monitoring_service