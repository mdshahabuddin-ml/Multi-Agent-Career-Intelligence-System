from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime

from backend.database import get_db
from backend.api import auth
from backend.services.monitoring_service import MonitoringService, get_monitoring_service, init_monitoring_service
from backend.schemas.monitoring import (
    MetricCreate, MetricQuery, MetricAggregation,
    AlertRuleCreate, AlertRuleUpdate, AlertRuleResponse,
    AlertResponse, AlertAcknowledge, AlertResolve, AlertSilence,
    HealthCheckCreate, HealthCheckUpdate, HealthCheckResponse,
    HealthCheckResultResponse,
    LogQuery, StructuredLogResponse, StructuredLogCreate,
    TraceCreate, TraceResponse, SpanCreate, SpanResponse,
    DashboardCreate, DashboardUpdate, DashboardResponse,
    DashboardPanelCreate, DashboardPanelUpdate, DashboardPanelResponse,
    NotificationChannelCreate, NotificationChannelUpdate, NotificationChannelResponse,
    NotificationTest,
    IncidentCreate, IncidentUpdate, IncidentResponse,
)
from backend.models.monitoring import StructuredLog

router = APIRouter(prefix="/monitoring", tags=["Monitoring"])


def get_monitoring(db: Session = Depends(get_db)) -> MonitoringService:
    return init_monitoring_service(db)


# ============= Metrics =============

@router.post("/metrics", response_model=dict, status_code=status.HTTP_201_CREATED)
async def record_metric(
    metric: MetricCreate,
    background_tasks: BackgroundTasks,
    current_user = Depends(auth.get_current_active_user),
    monitoring: MonitoringService = Depends(get_monitoring),
):
    """Record a metric value."""
    background_tasks.add_task(monitoring.record_metric, metric)
    return {"status": "accepted"}


@router.post("/metrics/batch", response_model=dict)
async def record_metrics_batch(
    metrics: List[MetricCreate],
    background_tasks: BackgroundTasks,
    current_user = Depends(auth.get_current_active_user),
    monitoring: MonitoringService = Depends(get_monitoring),
):
    """Record multiple metrics in batch."""
    background_tasks.add_task(monitoring.record_metric_batch, metrics)
    return {"status": "accepted", "count": len(metrics)}


@router.post("/metrics/query", response_model=List[dict])
async def query_metrics(
    query: MetricQuery,
    current_user = Depends(auth.get_current_active_user),
    monitoring: MonitoringService = Depends(get_monitoring),
):
    """Query metrics with filters."""
    metrics = monitoring.query_metrics(query)
    return [
        {
            "id": m.id,
            "name": m.name,
            "metric_type": m.metric_type.value,
            "value": m.value,
            "labels": m.labels,
            "source": m.source,
            "source_instance": m.source_instance,
            "organization_id": m.organization_id,
            "user_id": m.user_id,
            "timestamp": m.timestamp.isoformat(),
            "recorded_at": m.recorded_at.isoformat(),
            "metadata": m.metadata,
        }
        for m in metrics
    ]


@router.post("/metrics/aggregate", response_model=MetricAggregation)
async def aggregate_metrics(
    query: MetricQuery,
    current_user = Depends(auth.get_current_active_user),
    monitoring: MonitoringService = Depends(get_monitoring),
):
    """Aggregate metrics over time window."""
    return monitoring.aggregate_metrics(query)


@router.get("/metrics/names", response_model=List[str])
async def get_metric_names(
    source: Optional[str] = Query(None),
    current_user = Depends(auth.get_current_active_user),
    monitoring: MonitoringService = Depends(get_monitoring),
):
    """Get unique metric names."""
    return monitoring.get_metric_names(source)


# ============= Alert Rules =============

@router.post("/alert-rules", response_model=AlertRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_alert_rule(
    rule: AlertRuleCreate,
    current_user = Depends(auth.get_current_active_user),
    monitoring: MonitoringService = Depends(get_monitoring),
):
    """Create an alert rule."""
    rule = monitoring.create_alert_rule(rule, current_user.id)
    return AlertRuleResponse.from_orm(rule)


@router.get("/alert-rules", response_model=List[AlertRuleResponse])
async def list_alert_rules(
    organization_id: Optional[int] = Query(None),
    current_user = Depends(auth.get_current_active_user),
    monitoring: MonitoringService = Depends(get_monitoring),
):
    """List alert rules."""
    rules = monitoring.get_alert_rules(organization_id)
    return [AlertRuleResponse.from_orm(r) for r in rules]


@router.get("/alert-rules/{rule_id}", response_model=AlertRuleResponse)
async def get_alert_rule(
    rule_id: int,
    current_user = Depends(auth.get_current_active_user),
    monitoring: MonitoringService = Depends(get_monitoring),
):
    """Get alert rule by ID."""
    rule = monitoring.db.query(AlertRule).filter(AlertRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert rule not found")
    return AlertRuleResponse.from_orm(rule)


@router.patch("/alert-rules/{rule_id}", response_model=AlertRuleResponse)
async def update_alert_rule(
    rule_id: int,
    updates: AlertRuleUpdate,
    current_user = Depends(auth.get_current_active_user),
    monitoring: MonitoringService = Depends(get_monitoring),
):
    """Update an alert rule."""
    rule = monitoring.update_alert_rule(rule_id, updates)
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert rule not found")
    return AlertRuleResponse.from_orm(rule)


@router.delete("/alert-rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alert_rule(
    rule_id: int,
    current_user = Depends(auth.get_current_active_user),
    monitoring: MonitoringService = Depends(get_monitoring),
):
    """Delete an alert rule."""
    success = monitoring.delete_alert_rule(rule_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert rule not found")


@router.post("/alert-rules/evaluate", response_model=List[AlertResponse])
async def evaluate_alert_rules(
    background_tasks: BackgroundTasks,
    current_user = Depends(auth.get_current_active_user),
    monitoring: MonitoringService = Depends(get_monitoring),
):
    """Manually trigger alert rule evaluation."""
    alerts = monitoring.evaluate_alert_rules()
    return [AlertResponse.from_orm(a) for a in alerts]


# ============= Alerts =============

@router.get("/alerts", response_model=List[AlertResponse])
async def list_alerts(
    organization_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    current_user = Depends(auth.get_current_active_user),
    monitoring: MonitoringService = Depends(get_monitoring),
):
    """List alerts with filters."""
    alert_status = AlertStatus(status) if status else None
    alert_severity = AlertSeverity(severity) if severity else None
    alerts = monitoring.get_alerts(organization_id, alert_status, alert_severity, limit)
    return [AlertResponse.from_orm(a) for a in alerts]


@router.get("/alerts/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: int,
    current_user = Depends(auth.get_current_active_user),
    monitoring: MonitoringService = Depends(get_monitoring),
):
    """Get alert by ID."""
    alert = monitoring.db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    return AlertResponse.from_orm(alert)


@router.post("/alerts/{alert_id}/acknowledge", response_model=AlertResponse)
async def acknowledge_alert(
    alert_id: int,
    current_user = Depends(auth.get_current_active_user),
    monitoring: MonitoringService = Depends(get_monitoring),
):
    """Acknowledge an alert."""
    alert = monitoring.acknowledge_alert(alert_id, current_user.id)
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    return AlertResponse.from_orm(alert)


@router.post("/alerts/{alert_id}/resolve", response_model=AlertResponse)
async def resolve_alert(
    alert_id: int,
    current_user = Depends(auth.get_current_active_user),
    monitoring: MonitoringService = Depends(get_monitoring),
):
    """Resolve an alert."""
    alert = monitoring.resolve_alert(alert_id, current_user.id)
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    return AlertResponse.from_orm(alert)


@router.post("/alerts/{alert_id}/silence", response_model=AlertResponse)
async def silence_alert(
    alert_id: int,
    silenced_until: datetime = Query(...),
    current_user = Depends(auth.get_current_active_user),
    monitoring: MonitoringService = Depends(get_monitoring),
):
    """Silence an alert."""
    alert = monitoring.silence_alert(alert_id, silenced_until)
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    return AlertResponse.from_orm(alert)


# ============= Health Checks =============

@router.post("/health-checks", response_model=HealthCheckResponse, status_code=status.HTTP_201_CREATED)
async def create_health_check(
    check: HealthCheckCreate,
    current_user = Depends(auth.get_current_active_user),
    monitoring: MonitoringService = Depends(get_monitoring),
):
    """Create a health check."""
    check = monitoring.create_health_check(check, current_user.id)
    return HealthCheckResponse.from_orm(check)


@router.get("/health-checks", response_model=List[HealthCheckResponse])
async def list_health_checks(
    current_user = Depends(auth.get_current_active_user),
    monitoring: MonitoringService = Depends(get_monitoring),
):
    """List all health checks."""
    checks = monitoring.db.query(HealthCheck).filter(HealthCheck.enabled == True).all()
    return [HealthCheckResponse.from_orm(c) for c in checks]


@router.get("/health-checks/{check_id}", response_model=HealthCheckResponse)
async def get_health_check(
    check_id: int,
    current_user = Depends(auth.get_current_active_user),
    monitoring: MonitoringService = Depends(get_monitoring),
):
    """Get health check by ID."""
    check = monitoring.db.query(HealthCheck).filter(HealthCheck.id == check_id).first()
    if not check:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Health check not found")
    return HealthCheckResponse.from_orm(check)


@router.patch("/health-checks/{check_id}", response_model=HealthCheckResponse)
async def update_health_check(
    check_id: int,
    updates: HealthCheckUpdate,
    current_user = Depends(auth.get_current_active_user),
    monitoring: MonitoringService = Depends(get_monitoring),
):
    """Update a health check."""
    check = monitoring.update_health_check(check_id, updates)
    if not check:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Health check not found")
    return HealthCheckResponse.from_orm(check)


@router.delete("/health-checks/{check_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_health_check(
    check_id: int,
    current_user = Depends(auth.get_current_active_user),
    monitoring: MonitoringService = Depends(get_monitoring),
):
    """Delete a health check."""
    check = monitoring.db.query(HealthCheck).filter(HealthCheck.id == check_id).first()
    if not check:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Health check not found")
    monitoring.db.delete(check)
    monitoring.db.commit()


@router.post("/health-checks/{check_id}/run", response_model=HealthCheckResultResponse)
async def run_health_check(
    check_id: int,
    current_user = Depends(auth.get_current_active_user),
    monitoring: MonitoringService = Depends(get_monitoring),
):
    """Run a health check manually."""
    result = monitoring.run_health_check(check_id)
    return HealthCheckResultResponse.from_orm(result)


@router.post("/health-checks/run-all", response_model=List[HealthCheckResultResponse])
async def run_all_health_checks(
    background_tasks: BackgroundTasks,
    current_user = Depends(auth.get_current_active_user),
    monitoring: MonitoringService = Depends(get_monitoring),
):
    """Run all enabled health checks."""
    results = monitoring.run_all_health_checks()
    return [HealthCheckResultResponse.from_orm(r) for r in results]


@router.get("/health-checks/{check_id}/results", response_model=List[HealthCheckResultResponse])
async def get_health_check_results(
    check_id: int,
    limit: int = Query(50, le=200),
    current_user = Depends(auth.get_current_active_user),
    monitoring: MonitoringService = Depends(get_monitoring),
):
    """Get health check results."""
    results = monitoring.db.query(HealthCheckResult).filter(
        HealthCheckResult.check_id == check_id
    ).order_by(desc(HealthCheckResult.checked_at)).limit(limit).all()
    return [HealthCheckResultResponse.from_orm(r) for r in results]


# ============= Structured Logs =============

@router.post("/logs", response_model=StructuredLogResponse, status_code=status.HTTP_201_CREATED)
async def create_log(
    log: StructuredLogCreate,
    background_tasks: BackgroundTasks,
    current_user = Depends(auth.get_current_active_user),
    monitoring: MonitoringService = Depends(get_monitoring),
):
    """Create a structured log entry."""
    # Convert to model
    from backend.models.monitoring import StructuredLog as StructuredLogModel
    log_model = StructuredLogModel(
        timestamp=log.timestamp or datetime.utcnow(),
        level=log.level,
        logger_name=log.logger_name,
        service_name=log.service_name,
        instance_id=log.instance_id,
        message=log.message,
        message_template=log.message_template,
        trace_id=log.trace_id,
        span_id=log.span_id,
        user_id=log.user_id,
        organization_id=log.organization_id,
        session_id=log.session_id,
        request_id=log.request_id,
        fields=log.fields,
        exception_type=log.exception_type,
        exception_message=log.exception_message,
        stack_trace=log.stack_trace,
    )
    background_tasks.add_task(monitoring.log, log_model)
    return {"status": "accepted"}


@router.post("/logs/batch", response_model=dict)
async def create_logs_batch(
    logs: List[StructuredLogCreate],
    background_tasks: BackgroundTasks,
    current_user = Depends(auth.get_current_active_user),
    monitoring: MonitoringService = Depends(get_monitoring),
):
    """Create multiple log entries in batch."""
    from backend.models.monitoring import StructuredLog as StructuredLogModel
    log_models = [
        StructuredLogModel(
            timestamp=log.timestamp or datetime.utcnow(),
            level=log.level,
            logger_name=log.logger_name,
            service_name=log.service_name,
            instance_id=log.instance_id,
            message=log.message,
            message_template=log.message_template,
            trace_id=log.trace_id,
            span_id=log.span_id,
            user_id=log.user_id,
            organization_id=log.organization_id,
            session_id=log.session_id,
            request_id=log.request_id,
            fields=log.fields,
            exception_type=log.exception_type,
            exception_message=log.exception_message,
            stack_trace=log.stack_trace,
        )
        for log in logs
    ]
    background_tasks.add_task(monitoring.log_batch, log_models)
    return {"status": "accepted", "count": len(logs)}


@router.post("/logs/query", response_model=List[StructuredLogResponse])
async def query_logs(
    query: LogQuery,
    current_user = Depends(auth.get_current_active_user),
    monitoring: MonitoringService = Depends(get_monitoring),
):
    """Query structured logs."""
    logs = monitoring.query_logs(query)
    return [StructuredLogResponse.from_orm(l) for l in logs]


# ============= Distributed Tracing =============

@router.post("/traces", response_model=TraceResponse, status_code=status.HTTP_201_CREATED)
async def create_trace(
    trace: TraceCreate,
    background_tasks: BackgroundTasks,
    current_user = Depends(auth.get_current_active_user),
    monitoring: MonitoringService = Depends(get_monitoring),
):
    """Create a trace."""
    background_tasks.add_task(monitoring.create_trace, trace)
    return {"status": "accepted"}


@router.post("/traces/batch", response_model=dict)
async def create_traces_batch(
    traces: List[TraceCreate],
    background_tasks: BackgroundTasks,
    current_user = Depends(auth.get_current_active_user),
    monitoring: MonitoringService = Depends(get_monitoring),
):
    """Create multiple traces in batch."""
    for trace in traces:
        background_tasks.add_task(monitoring.create_trace, trace)
    return {"status": "accepted", "count": len(traces)}


@router.post("/spans", response_model=SpanResponse, status_code=status.HTTP_201_CREATED)
async def create_span(
    span: SpanCreate,
    background_tasks: BackgroundTasks,
    current_user = Depends(auth.get_current_active_user),
    monitoring: MonitoringService = Depends(get_monitoring),
):
    """Create a span."""
    background_tasks.add_task(monitoring.create_span, span)
    return {"status": "accepted"}


@router.get("/traces/{trace_id}", response_model=TraceResponse)
async def get_trace(
    trace_id: str,
    current_user = Depends(auth.get_current_active_user),
    monitoring: MonitoringService = Depends(get_monitoring),
):
    """Get trace by ID."""
    trace = monitoring.get_trace(trace_id)
    if not trace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trace not found")
    return TraceResponse.from_orm(trace)


@router.get("/traces/{trace_id}/spans", response_model=TraceResponse)
async def get_trace_with_spans(
    trace_id: str,
    current_user = Depends(auth.get_current_active_user),
    monitoring: MonitoringService = Depends(get_monitoring),
):
    """Get trace with all spans."""
    trace = monitoring.get_trace_with_spans(trace_id)
    if not trace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trace not found")
    return TraceResponse.from_orm(trace)


@router.get("/traces", response_model=List[TraceResponse])
async def query_traces(
    service_name: Optional[str] = Query(None),
    operation_name: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    user_id: Optional[int] = Query(None),
    organization_id: Optional[int] = Query(None),
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    limit: int = Query(100, le=500),
    current_user = Depends(auth.get_current_active_user),
    monitoring: MonitoringService = Depends(get_monitoring),
):
    """Query traces with filters."""
    trace_status = TraceStatus(status) if status else None
    traces = monitoring.query_traces(
        service_name=service_name,
        operation_name=operation_name,
        status=trace_status,
        user_id=user_id,
        organization_id=organization_id,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
    )
    return [TraceResponse.from_orm(t) for t in traces]


# ============= Dashboards =============

@router.post("/dashboards", response_model=DashboardResponse, status_code=status.HTTP_201_CREATED)
async def create_dashboard(
    dashboard: DashboardCreate,
    current_user = Depends(auth.get_current_active_user),
    monitoring: MonitoringService = Depends(get_monitoring),
):
    """Create a dashboard."""
    dash = monitoring.create_dashboard(dashboard, current_user.id)
    return DashboardResponse.from_orm(dash)


@router.get("/dashboards", response_model=List[DashboardResponse])
async def list_dashboards(
    organization_id: Optional[int] = Query(None),
    current_user = Depends(auth.get_current_active_user),
    monitoring: MonitoringService = Depends(get_monitoring),
):
    """List dashboards."""
    dashboards = monitoring.list_dashboards(organization_id)
    return [DashboardResponse.from_orm(d) for d in dashboards]


@router.get("/dashboards/{dashboard_id}", response_model=DashboardResponse)
async def get_dashboard(
    dashboard_id: int,
    current_user = Depends(auth.get_current_active_user),
    monitoring: MonitoringService = Depends(get_monitoring),
):
    """Get dashboard by ID."""
    dashboard = monitoring.get_dashboard(dashboard_id)
    if not dashboard:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dashboard not found")
    return DashboardResponse.from_orm(dashboard)


@router.get("/dashboards/slug/{slug}", response_model=DashboardResponse)
async def get_dashboard_by_slug(
    slug: str,
    current_user = Depends(auth.get_current_active_user),
    monitoring: MonitoringService = Depends(get_monitoring),
):
    """Get dashboard by slug."""
    dashboard = monitoring.get_dashboard_by_slug(slug)
    if not dashboard:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dashboard not found")
    return DashboardResponse.from_orm(dashboard)


@router.patch("/dashboards/{dashboard_id}", response_model=DashboardResponse)
async def update_dashboard(
    dashboard_id: int,
    updates: DashboardUpdate,
    current_user = Depends(auth.get_current_active_user),
    monitoring: MonitoringService = Depends(get_monitoring),
):
    """Update a dashboard."""
    dashboard = monitoring.update_dashboard(dashboard_id, updates)
    if not dashboard:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dashboard not found")
    return DashboardResponse.from_orm(dashboard)


@router.delete("/dashboards/{dashboard_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dashboard(
    dashboard_id: int,
    current_user = Depends(auth.get_current_active_user),
    monitoring: MonitoringService = Depends(get_monitoring),
):
    """Delete a dashboard."""
    dashboard = monitoring.get_dashboard(dashboard_id)
    if not dashboard:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dashboard not found")
    monitoring.db.delete(dashboard)
    monitoring.db.commit()


@router.post("/dashboards/{dashboard_id}/panels", response_model=DashboardPanelResponse, status_code=status.HTTP_201_CREATED)
async def add_dashboard_panel(
    dashboard_id: int,
    panel: DashboardPanelCreate,
    current_user = Depends(auth.get_current_active_user),
    monitoring: MonitoringService = Depends(get_monitoring),
):
    """Add a panel to dashboard."""
    panel = monitoring.add_dashboard_panel(panel)
    return DashboardPanelResponse.from_orm(panel)


@router.patch("/panels/{panel_id}", response_model=DashboardPanelResponse)
async def update_dashboard_panel(
    panel_id: int,
    updates: DashboardPanelUpdate,
    current_user = Depends(auth.get_current_active_user),
    monitoring: MonitoringService = Depends(get_monitoring),
):
    """Update a dashboard panel."""
    panel = monitoring.update_dashboard_panel(panel_id, updates)
    if not panel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Panel not found")
    return DashboardPanelResponse.from_orm(panel)


@router.delete("/panels/{panel_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dashboard_panel(
    panel_id: int,
    current_user = Depends(auth.get_current_active_user),
    monitoring: MonitoringService = Depends(get_monitoring),
):
    """Delete a dashboard panel."""
    panel = monitoring.db.query(DashboardPanel).filter(DashboardPanel.id == panel_id).first()
    if not panel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Panel not found")
    monitoring.db.delete(panel)
    monitoring.db.commit()


# ============= Notification Channels =============

@router.post("/notification-channels", response_model=NotificationChannelResponse, status_code=status.HTTP_201_CREATED)
async def create_notification_channel(
    channel: NotificationChannelCreate,
    current_user = Depends(auth.get_current_active_user),
    monitoring: MonitoringService = Depends(get_monitoring),
):
    """Create a notification channel."""
    channel = monitoring.create_notification_channel(channel, current_user.id)
    return NotificationChannelResponse.from_orm(channel)


@router.get("/notification-channels", response_model=List[NotificationChannelResponse])
async def list_notification_channels(
    current_user = Depends(auth.get_current_active_user),
    monitoring: MonitoringService = Depends(get_monitoring),
):
    """List notification channels."""
    channels = monitoring.db.query(NotificationChannel).filter(NotificationChannel.enabled == True).all()
    return [NotificationChannelResponse.from_orm(c) for c in channels]


@router.post("/notification-channels/test", response_model=dict)
async def test_notification_channel(
    test: NotificationTest,
    current_user = Depends(auth.get_current_active_user),
    monitoring: MonitoringService = Depends(get_monitoring),
):
    """Test a notification channel."""
    return monitoring.test_notification_channel(test)


# ============= Incidents =============

@router.post("/incidents", response_model=IncidentResponse, status_code=status.HTTP_201_CREATED)
async def create_incident(
    incident: IncidentCreate,
    current_user = Depends(auth.get_current_active_user),
    monitoring: MonitoringService = Depends(get_monitoring),
):
    """Create an incident."""
    inc = monitoring.create_incident(incident, current_user.id)
    return IncidentResponse.from_orm(inc)


@router.get("/incidents", response_model=List[IncidentResponse])
async def list_incidents(
    organization_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    current_user = Depends(auth.get_current_active_user),
    monitoring: MonitoringService = Depends(get_monitoring),
):
    """List incidents."""
    inc_severity = AlertSeverity(severity) if severity else None
    incidents = monitoring.get_incidents(organization_id, status, inc_severity, limit)
    return [IncidentResponse.from_orm(i) for i in incidents]


@router.get("/incidents/{incident_id}", response_model=IncidentResponse)
async def get_incident(
    incident_id: int,
    current_user = Depends(auth.get_current_active_user),
    monitoring: MonitoringService = Depends(get_monitoring),
):
    """Get incident by ID."""
    incident = monitoring.db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    return IncidentResponse.from_orm(incident)


@router.patch("/incidents/{incident_id}", response_model=IncidentResponse)
async def update_incident(
    incident_id: int,
    updates: IncidentUpdate,
    current_user = Depends(auth.get_current_active_user),
    monitoring: MonitoringService = Depends(get_monitoring),
):
    """Update an incident."""
    incident = monitoring.update_incident(incident_id, updates)
    if not incident:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    return IncidentResponse.from_orm(incident)