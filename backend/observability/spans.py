"""
Span helpers: sync/async context managers and a decorator.

Usage (additive — behaviour is identical when export is disabled)::

    from backend.observability import span
    from backend.observability.conventions import SPAN_KIND_TOOL, ATTR_LAYER, LAYER_SOCIAL

    with span("social.fetch", kind=SPAN_KIND_TOOL,
              attributes={ATTR_LAYER: LAYER_SOCIAL, "platform": "youtube"}) as s:
        ...
        s.set_attribute("output.value", "...")

Exceptions propagate after being recorded on the span (message only —
never attach tokens, credentials, or request bodies with secrets).
"""

from __future__ import annotations

import functools
from typing import Any, Callable, Dict, Optional

from backend.observability import conventions as C
from backend.observability.tracing import get_tracer


def _status_error() -> Any:
    try:
        from opentelemetry.trace import Status, StatusCode

        return Status(StatusCode.ERROR)
    except ImportError:
        return "ERROR"


def _status_ok() -> Any:
    try:
        from opentelemetry.trace import Status, StatusCode

        return Status(StatusCode.OK)
    except ImportError:
        return "OK"


class span:
    """Sync + async context manager creating one span."""

    def __init__(self, name: str, kind: str = C.SPAN_KIND_CHAIN,
                 attributes: Optional[Dict[str, Any]] = None,
                 tracer_name: str = "careerintel") -> None:
        self._name = name
        self._kind = kind
        self._attributes = dict(attributes or {})
        self._tracer_name = tracer_name
        self._span: Any = None
        self.current: Any = None

    def _start(self) -> Any:
        tracer = get_tracer(self._tracer_name)
        attributes = {C.OPENINFERENCE_SPAN_KIND: self._kind}
        for key, value in self._attributes.items():
            if value is not None:
                attributes[key] = value
        self._span = tracer.start_span(self._name, attributes=attributes)
        self.current = self._span
        return self._span

    def _fail(self, exc: BaseException) -> None:
        try:
            self._span.record_exception(exc)
        except Exception:  # pragma: no cover - defensive
            pass
        try:
            self._span.set_status(_status_error())
        except Exception:  # pragma: no cover - defensive
            pass

    def _succeed(self) -> None:
        try:
            self._span.set_status(_status_ok())
        except Exception:  # pragma: no cover - defensive
            pass

    def _end(self) -> None:
        try:
            self._span.end()
        except Exception:  # pragma: no cover - defensive
            pass

    def __enter__(self) -> Any:
        return self._start()

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
        if exc is None:
            self._succeed()
        else:
            self._fail(exc)
        self._end()
        return False

    async def __aenter__(self) -> Any:
        return self._start()

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
        if exc is None:
            self._succeed()
        else:
            self._fail(exc)
        self._end()
        return False


def traced(name: Optional[str] = None, kind: str = C.SPAN_KIND_CHAIN,
           attributes: Optional[Dict[str, Any]] = None,
           tracer_name: str = "careerintel") -> Callable:
    """Decorator wrapping a sync or async function in a span."""

    def _wrap(func: Callable) -> Callable:
        span_name = name or f"{func.__module__}.{func.__qualname__}"

        if _is_coro(func):
            @functools.wraps(func)
            async def _async_inner(*args: Any, **kwargs: Any) -> Any:
                async with span(span_name, kind=kind, attributes=attributes,
                                tracer_name=tracer_name):
                    return await func(*args, **kwargs)

            return _async_inner

        @functools.wraps(func)
        def _sync_inner(*args: Any, **kwargs: Any) -> Any:
            with span(span_name, kind=kind, attributes=attributes,
                      tracer_name=tracer_name):
                return func(*args, **kwargs)

        return _sync_inner

    return _wrap


def _is_coro(func: Callable) -> bool:
    import asyncio

    return asyncio.iscoroutinefunction(func)
