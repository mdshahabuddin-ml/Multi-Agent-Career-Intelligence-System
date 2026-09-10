"""
Tests for the observability base layer (OpenInference/OpenTelemetry → Phoenix).

Design under test: everything degrades to a no-op when export is disabled
or the OTel packages are absent — these tests run WITHOUT the OTel
packages installed and assert the app stays fully functional.

Isolation: imports only backend.observability (+ stdlib). No career,
content, or Hermes imports.
"""

from __future__ import annotations

import pytest

from backend.observability import (
    get_tracer,
    instrument_openai,
    is_enabled,
    setup_observability,
    span,
    traced,
)
from backend.observability import conventions as C
from backend.observability.bridge import (
    record_finished_span,
    span_to_span_payload,
    span_to_trace_payload,
)
from backend.observability.tracing import _read_setting


@pytest.fixture(autouse=True)
def _otel_off(monkeypatch):
    monkeypatch.delenv("OTEL_ENABLED", raising=False)
    import backend.observability.tracing as tracing

    monkeypatch.setattr(tracing, "_configured", False)
    monkeypatch.setattr(tracing, "_tracer_provider", None)
    yield
    monkeypatch.setattr(tracing, "_configured", False)
    monkeypatch.setattr(tracing, "_tracer_provider", None)


class TestDisabledByDefault:
    def test_is_enabled_false_without_env(self):
        assert is_enabled() is False

    def test_setup_returns_false_and_never_raises(self):
        assert setup_observability() is False
        assert setup_observability() is False  # idempotent

    def test_instrument_openai_noop_when_disabled(self):
        assert instrument_openai() is False

    def test_read_setting_prefers_default(self):
        assert _read_setting("OTEL_ENABLED_DEFINITELY_ABSENT_XYZ", "fallback") == "fallback"


class TestNoOpTracer:
    def test_span_lifecycle_without_sdk(self):
        tracer = get_tracer("test")
        s = tracer.start_span("op", attributes={"k": "v"})
        s.set_attribute("k2", 1)
        s.set_status("OK")
        s.end()  # must not raise

    def test_sync_context_manager(self):
        with span("sync.op", kind=C.SPAN_KIND_TOOL,
                  attributes={C.ATTR_LAYER: C.LAYER_SOCIAL}) as s:
            s.set_attribute("platform", "youtube")

    def test_sync_exception_propagates(self):
        with pytest.raises(ValueError, match="boom"):
            with span("sync.fail"):
                raise ValueError("boom")

    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        async with span("async.op", kind=C.SPAN_KIND_AGENT) as s:
            s.set_attribute("k", "v")

    @pytest.mark.asyncio
    async def test_async_exception_propagates(self):
        with pytest.raises(RuntimeError):
            async with span("async.fail"):
                raise RuntimeError("nope")

    def test_traced_decorator_sync(self):
        @traced("unit.work", kind=C.SPAN_KIND_CHAIN)
        def work(x):
            return x * 2

        assert work(21) == 42
        assert work.__name__ == "work"

    @pytest.mark.asyncio
    async def test_traced_decorator_async(self):
        @traced(kind=C.SPAN_KIND_TOOL)
        async def fetch():
            return "ok"

        assert await fetch() == "ok"


class TestConventions:
    def test_kinds_cover_pipeline(self):
        for kind in (C.SPAN_KIND_LLM, C.SPAN_KIND_CHAIN, C.SPAN_KIND_AGENT,
                     C.SPAN_KIND_TOOL, C.SPAN_KIND_RETRIEVER,
                     C.SPAN_KIND_EMBEDDING, C.SPAN_KIND_RERANKER):
            assert isinstance(kind, str) and kind

    def test_layers_cover_diagram(self):
        for layer in (C.LAYER_CAREER, C.LAYER_HERMES, C.LAYER_MEMORY,
                      C.LAYER_SKILLS, C.LAYER_AUTOMATION, C.LAYER_CONTENT,
                      C.LAYER_SOCIAL, C.LAYER_OBSERVABILITY):
            assert isinstance(layer, str) and layer


def _record(name="social.fetch"):
    return {
        "name": name,
        "span_id": "s1",
        "trace_id": "t1",
        "attributes": {
            "openinference.span.kind": "TOOL",
            "careerintel.layer": "social_apis",
            "careerintel.platform": "youtube",
        },
    }


class TestBridge:
    def test_trace_payload_shape(self):
        payload = span_to_trace_payload(_record(), user_id=7)
        assert payload["trace_id"] == "t1"
        assert payload["operation_name"] == "social.fetch"
        assert payload["status"] == "OK"
        assert payload["user_id"] == 7
        assert payload["tags"] == {"layer": "social_apis"}
        assert payload["trace_metadata"]["careerintel.platform"] == "youtube"

    def test_span_payload_shape_and_duration(self):
        from datetime import datetime, timedelta

        start = datetime(2026, 1, 1, 0, 0, 0)
        rec = _record()
        rec["start_time"] = start
        rec["end_time"] = start + timedelta(seconds=2)
        payload = span_to_span_payload(rec, "t1")
        assert payload["trace_id"] == "t1"
        assert payload["span_id"] == "s1"
        assert payload["duration_ms"] == pytest.approx(2000.0)
        assert payload["tags"] == {"kind": "TOOL"}

    def test_error_mapping_and_secret_free_metadata(self):
        rec = _record()
        rec["error"] = "boom"
        rec["attributes"] = dict(rec["attributes"])
        rec["attributes"]["exception.traceback"] = "should be filtered"
        trace = span_to_trace_payload(rec)
        assert trace["status"] == "ERROR"
        assert trace["error_message"] == "boom"
        assert "exception.traceback" not in trace["trace_metadata"]

    def test_record_finished_span_never_raises_without_db(self):
        assert record_finished_span(None, _record()) is False
