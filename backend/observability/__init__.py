"""
Observability base layer: OpenInference conventions + OpenTelemetry → Phoenix.

Architecture position (bottom of the stack diagram):
    Existing Career Intelligence / Agents / RAG / Tools / Workers
      → Hermes Engine → Memory | Skills | Automation
        → Content Engine → Social OAuth/APIs
          → **OpenInference / OpenTelemetry → Phoenix** (this package)

Design rules (load-bearing):
- BRIDGE, never replace: finished spans can be mirrored into the existing
  ``Trace``/``Span``/``AgentExecution`` tables (see ``bridge.py``) so
  Grafana/DB views keep working; Phoenix receives the same data over OTLP.
- DISABLED-SAFE: everything is a no-op unless ``OTEL_ENABLED=true`` AND the
  OTel SDK is importable. The app must boot and serve identically with the
  packages absent — all SDK imports are lazy and guarded.
- NO SECRETS IN SPANS: attribute values are caller-supplied; never attach
  tokens, keys, passwords, or request bodies containing credentials.
"""

from backend.observability.spans import span, traced
from backend.observability.tracing import (
    get_tracer,
    instrument_openai,
    is_enabled,
    setup_observability,
)

__all__ = [
    "span",
    "traced",
    "get_tracer",
    "instrument_openai",
    "is_enabled",
    "setup_observability",
]

__version__ = "0.1.0"
