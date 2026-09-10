"""
DB bridge: mirror finished OTel spans into the existing Trace/Span tables.

This keeps Grafana and the ``/api/monitoring`` views working on the same
data Phoenix receives over OTLP — one instrumentation point, two backends,
zero duplication of the tracing logic itself.

- ``span_to_trace_payload`` / ``span_to_span_payload`` are pure mappers
  (span-record dict → ``TraceCreate``/``SpanCreate``-shaped dicts).
- ``record_finished_span`` persists via ``MonitoringService`` using lazy
  imports and ``getattr`` guards; any failure is swallowed (observability
  must never break product paths).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def span_to_trace_payload(span: Dict[str, Any], service_name: str = "careerintel-backend",
                          user_id: Optional[int] = None) -> Dict[str, Any]:
    """Map a finished-span record to a ``TraceCreate``-shaped payload."""
    attributes = dict(span.get("attributes") or {})
    return {
        "trace_id": str(span.get("trace_id") or span.get("span_id") or "trace-unknown"),
        "service_name": service_name,
        "operation_name": str(span.get("name") or "unknown")[:255],
        "start_time": span.get("start_time") or _utcnow(),
        "end_time": span.get("end_time"),
        "status": "ERROR" if span.get("error") else "OK",
        "error_message": (str(span.get("error"))[:2000] if span.get("error") else None),
        "user_id": user_id,
        "tags": {"layer": str(attributes.get("careerintel.layer", "observability"))},
        "trace_metadata": {k: v for k, v in attributes.items()
                           if not k.startswith("exception.")},
    }


def span_to_span_payload(span: Dict[str, Any], trace_id: str,
                         service_name: str = "careerintel-backend",
                         user_id: Optional[int] = None) -> Dict[str, Any]:
    """Map a finished-span record to a ``SpanCreate``-shaped payload."""
    attributes = dict(span.get("attributes") or {})
    start = span.get("start_time")
    end = span.get("end_time")
    duration_ms: Optional[float] = None
    try:
        if start and end:
            duration_ms = (end - start).total_seconds() * 1000.0
    except Exception:  # pragma: no cover - defensive
        duration_ms = None
    return {
        "trace_id": trace_id,
        "span_id": str(span.get("span_id") or "span-unknown"),
        "parent_span_id": span.get("parent_span_id"),
        "service_name": service_name,
        "operation_name": str(span.get("name") or "unknown")[:255],
        "start_time": start or _utcnow(),
        "end_time": end,
        "duration_ms": duration_ms,
        "status": "ERROR" if span.get("error") else "OK",
        "error_message": (str(span.get("error"))[:2000] if span.get("error") else None),
        "user_id": user_id,
        "tags": {"kind": str(attributes.get("openinference.span.kind", "CHAIN"))},
        "span_metadata": {k: v for k, v in attributes.items()
                          if not k.startswith("exception.")},
    }


def record_finished_span(db: Any, span: Dict[str, Any],
                         service_name: str = "careerintel-backend",
                         user_id: Optional[int] = None) -> bool:
    """Persist one finished span via ``MonitoringService``. Never raises."""
    try:
        from backend.services.monitoring_service import MonitoringService

        service = MonitoringService(db)
        create_trace = getattr(service, "create_trace", None)
        create_span = getattr(service, "create_span", None)
        if create_trace is None or create_span is None:
            return False
        trace_payload = span_to_trace_payload(span, service_name, user_id)
        trace_id = trace_payload["trace_id"]
        try:
            create_trace(trace_payload)  # type: ignore[arg-type]
        except Exception as exc:  # trace may already exist for this id
            logger.debug("Trace mirror skipped: %s", exc)
        create_span(span_to_span_payload(span, trace_id, service_name, user_id))  # type: ignore[arg-type]
        return True
    except Exception as exc:  # noqa: BLE001 - observability never breaks product
        logger.debug("Span mirror failed: %s", exc)
        return False
