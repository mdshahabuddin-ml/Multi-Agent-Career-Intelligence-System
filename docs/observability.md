# Observability — OpenInference / OpenTelemetry → Phoenix

Bottom layer of the architecture:

```
Existing Career Intelligence / Agents / RAG / Tools / Workers
  → Hermes Engine → Memory | Skills | Automation
    → Content Engine → Social OAuth/APIs
      → OpenInference / OpenTelemetry → Phoenix   ← this document
```

## What it is

- **Spans** (`backend/observability/spans.py`): sync/async `span()` context
  managers + `@traced` decorator. Attribute keys follow the OpenInference
  semantic conventions (`backend/observability/conventions.py`).
- **Lifecycle** (`backend/observability/tracing.py`): lazy, idempotent
  `setup_observability()` + `instrument_openai()` (OpenInference OpenAI
  instrumentor for the evaluation LLM judges). Both degrade to no-ops when
  `OTEL_ENABLED` is false or the packages are not installed.
- **Bridge** (`backend/observability/bridge.py`): mirrors finished spans
  into the existing `traces`/`spans` tables via `MonitoringService`, so
  Grafana and `/api/monitoring` keep working on the same data Phoenix
  receives over OTLP. It extends — never replaces — existing tracing.
- **Currently instrumented** (additive spans, zero behavior change):
  `ContentAnalyticsService.refresh_snapshot` and
  `HermesContentOptimizationLoop.analyse` / `.run`.

## Enable

```bash
pip install -r requirements.txt   # adds otel SDK + OI openai instrumentor
docker compose up -d phoenix      # trace UI at http://localhost:6006
```

```
OTEL_ENABLED=true
OTEL_SERVICE_NAME=careerintel-backend
PHOENIX_OTLP_ENDPOINT=http://localhost:4318/v1/traces   # http://phoenix:4318/v1/traces in compose
```

With `OTEL_ENABLED=false` (default) the app boots and serves identically;
the OTel imports are lazy, so the packages may even be absent.

## Rules

1. Never attach secrets to spans (tokens, keys, passwords, credentialed bodies).
2. Unsupported platform metrics stay `None` — observability records the
   *fact* of a refresh, never fabricated measurements.
3. New instrumentation goes through `backend/observability.span`, not new
   tracing frameworks. No LangSmith backend, no second vector DB, no new
   agent framework — those capabilities already exist in this repo.
