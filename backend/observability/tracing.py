"""
Tracer lifecycle: lazy OpenTelemetry setup with graceful degradation.

- ``setup_observability()`` is idempotent and safe to call anywhere; it
  configures an OTLP/HTTP span exporter ONLY when ``OTEL_ENABLED`` is true
  and the SDK imports succeed. Otherwise the process keeps a no-op tracer.
- ``get_tracer(name)`` auto-initializes once and always returns a usable
  tracer object (SDK or no-op) — callers never branch on availability.
- ``instrument_openai()`` attaches the OpenInference OpenAI instrumentor
  when that package is present; otherwise a silent no-op.

All ``backend.config.settings`` reads are lazy (function scope) so importing
this module can never create import cycles or require env at import time.
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Optional

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_configured = False
_tracer_provider: Any = None
_openai_instrumented = False


def _read_setting(name: str, default: Any) -> Any:
    """Read from Settings first, environment second, default last."""
    try:
        from backend.config import settings

        value = getattr(settings, name, None)
        if value is not None:
            return value
    except Exception:  # pragma: no cover - config must never break tracing
        pass
    import os

    return os.environ.get(name, default)


def is_enabled() -> bool:
    """True only when observability export is explicitly switched on."""
    value = _read_setting("OTEL_ENABLED", False)
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "on")
    return bool(value)


def setup_observability() -> bool:
    """Configure the global tracer provider. Returns True when exporting.

    Safe to call repeatedly and safe when the OTel packages are missing —
    returns False and leaves a no-op tracer in place.
    """
    global _configured, _tracer_provider
    with _lock:
        if _configured:
            return _tracer_provider is not None
        _configured = True
        if not is_enabled():
            return False
        try:
            from opentelemetry import trace
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
                OTLPSpanExporter,
            )
            from opentelemetry.sdk.resources import Resource
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor
        except ImportError:
            logger.info("OpenTelemetry SDK not installed; tracing stays disabled.")
            return False
        try:
            service_name = str(_read_setting("OTEL_SERVICE_NAME", "careerintel-backend"))
            endpoint = str(_read_setting(
                "PHOENIX_OTLP_ENDPOINT", "http://localhost:4318/v1/traces"))
            provider = TracerProvider(
                resource=Resource.create({"service.name": service_name}))
            provider.add_span_processor(
                BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
            trace.set_tracer_provider(provider)
            _tracer_provider = provider
            logger.info("Observability exporting to %s", endpoint)
            return True
        except Exception as exc:  # noqa: BLE001 - export must never break the app
            logger.warning("Observability setup failed; tracing disabled: %s", exc)
            _tracer_provider = None
            return False


class _NoOpSpan:
    """Minimal span surface used when exporting is off."""

    def __init__(self) -> None:
        self.attributes: dict[str, Any] = {}
        self.status: Any = None

    def set_attribute(self, key: str, value: Any) -> None:
        self.attributes[key] = value

    def set_status(self, status: Any) -> None:
        self.status = status

    def record_exception(self, exception: BaseException) -> None:
        self.attributes["exception.message"] = str(exception)[:500]

    def end(self) -> None:
        pass


class _NoOpTracer:
    def start_span(self, name: str, attributes: Optional[dict] = None) -> _NoOpSpan:
        span = _NoOpSpan()
        for key, value in (attributes or {}).items():
            span.set_attribute(key, value)
        return span


_NOOP_TRACER = _NoOpTracer()


def get_tracer(name: str = "careerintel") -> Any:
    """Return a tracer (SDK-backed when exporting, no-op otherwise)."""
    setup_observability()
    if _tracer_provider is not None:
        try:
            from opentelemetry import trace

            return trace.get_tracer(name)
        except Exception:  # pragma: no cover - defensive
            pass
    return _NOOP_TRACER


def instrument_openai() -> bool:
    """Attach OpenInference OpenAI instrumentation when available.

    Makes ``AsyncOpenAI`` calls (e.g. the evaluation LLM judges) appear as
    LLM spans in Phoenix. No-op when the package is missing or export is off.
    """
    global _openai_instrumented
    if _openai_instrumented:
        return True
    if not is_enabled():
        return False
    try:
        from openinference.instrumentation.openai import OpenAIInstrumentor

        OpenAIInstrumentor().instrument()
        _openai_instrumented = True
        return True
    except ImportError:
        logger.info("openinference-instrumentation-openai not installed; skipping.")
        return False
    except Exception as exc:  # noqa: BLE001 - never break the app
        logger.warning("OpenAI instrumentation failed: %s", exc)
        return False
