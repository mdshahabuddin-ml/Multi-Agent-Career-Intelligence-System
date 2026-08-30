"""Request/Response logging middleware."""

import time
import uuid
import logging
import json
from typing import Callable, Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse
from starlette.types import ASGIApp

logger = logging.getLogger("request_logger")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging HTTP requests and responses."""

    def __init__(
        self,
        app: ASGIApp,
        log_requests: bool = True,
        log_responses: bool = True,
        log_request_body: bool = False,
        log_response_body: bool = False,
        excluded_paths: Optional[set] = None,
        sensitive_headers: Optional[set] = None,
        max_body_length: int = 10000,
    ):
        super().__init__(app)
        self.log_requests = log_requests
        self.log_responses = log_responses
        self.log_request_body = log_request_body
        self.log_response_body = log_response_body
        self.excluded_paths = excluded_paths or {
            "/health",
            "/metrics",
            "/favicon.ico",
            "/docs",
            "/openapi.json",
            "/redoc",
        }
        self.sensitive_headers = sensitive_headers or {
            "authorization",
            "cookie",
            "x-api-key",
            "x-csrf-token",
            "x-forwarded-for",
            "x-real-ip",
        }
        self.max_body_length = max_body_length

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip logging for excluded paths
        if request.url.path in self.excluded_paths:
            return await call_next(request)

        # Generate request ID
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id

        # Start timing
        start_time = time.perf_counter()

        # Log request
        if self.log_requests:
            await self._log_request(request, request_id)

        # Process request
        try:
            response = await call_next(request)
        except Exception as e:
            # Log exception
            duration = time.perf_counter() - start_time
            logger.error(
                f"Request {request_id} failed after {duration:.3f}s: {type(e).__name__}: {e}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": round(duration * 1000, 2),
                    "error": str(e),
                },
                exc_info=True,
            )
            raise

        # Calculate duration
        duration = time.perf_counter() - start_time

        # Log response
        if self.log_responses:
            await self._log_response(request, response, request_id, duration)

        # Add timing headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{duration:.3f}s"

        return response

    async def _log_request(self, request: Request, request_id: str):
        """Log incoming request details."""
        # Get client info
        client_host = request.client.host if request.client else "unknown"
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            client_host = forwarded_for.split(",")[0].strip()

        # Build log data
        log_data = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "query": str(request.url.query) if request.url.query else None,
            "client_ip": client_host,
            "user_agent": request.headers.get("user-agent"),
            "content_type": request.headers.get("content-type"),
            "content_length": request.headers.get("content-length"),
        }

        # Add headers (filtered)
        headers = {}
        for k, v in request.headers.items():
            if k.lower() not in self.sensitive_headers:
                headers[k] = v
        if headers:
            log_data["headers"] = headers

        # Add request body if enabled
        if self.log_request_body and request.method in ("POST", "PUT", "PATCH"):
            try:
                body = await request.body()
                if body:
                    content_type = request.headers.get("content-type", "")
                    if "json" in content_type:
                        try:
                            log_data["body"] = json.loads(body.decode())
                        except json.JSONDecodeError:
                            log_data["body"] = body.decode()[:self.max_body_length]
                    elif "form" in content_type or "multipart" in content_type:
                        log_data["body"] = "[form data]"
                    else:
                        text = body.decode()[:self.max_body_length]
                        log_data["body"] = text
            except Exception:
                log_data["body"] = "[unreadable]"

        logger.info(
            f"Request {request_id}: {request.method} {request.url.path}",
            extra=log_data,
        )

    async def _log_response(
        self,
        request: Request,
        response: Response,
        request_id: str,
        duration: float,
    ):
        """Log response details."""
        log_data = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": round(duration * 1000, 2),
            "content_type": response.headers.get("content-type"),
            "content_length": response.headers.get("content-length"),
        }

        # Add response headers (filtered)
        headers = {}
        for k, v in response.headers.items():
            if k.lower() not in self.sensitive_headers:
                headers[k] = v
        if headers:
            log_data["headers"] = headers

        # Add response body if enabled
        if self.log_response_body and response.status_code < 400:
            try:
                # Only log body for JSON responses
                content_type = response.headers.get("content-type", "")
                if "json" in content_type:
                    if isinstance(response, StreamingResponse):
                        # Can't read streaming response body without consuming it
                        log_data["body"] = "[streaming]"
                    else:
                        body = b""
                        async for chunk in response.body_iterator:
                            body += chunk
                        if body:
                            try:
                                log_data["body"] = json.loads(body.decode())
                            except json.JSONDecodeError:
                                log_data["body"] = body.decode()[:self.max_body_length]
                        # Recreate response with body
                        response = Response(
                            content=body,
                            status_code=response.status_code,
                            headers=dict(response.headers),
                            media_type=response.media_type,
                        )
            except Exception:
                log_data["body"] = "[unreadable]"

        # Log at appropriate level based on status code
        if response.status_code >= 500:
            logger.error(
                f"Response {request_id}: {response.status_code} {request.method} {request.url.path} ({duration:.3f}s)",
                extra=log_data,
            )
        elif response.status_code >= 400:
            logger.warning(
                f"Response {request_id}: {response.status_code} {request.method} {request.url.path} ({duration:.3f}s)",
                extra=log_data,
            )
        else:
            logger.info(
                f"Response {request_id}: {response.status_code} {request.method} {request.url.path} ({duration:.3f}s)",
                extra=log_data,
            )

        return response


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """Structured JSON logging middleware for log aggregation."""

    def __init__(
        self,
        app: ASGIApp,
        logger_name: str = "structured",
        include_trace: bool = True,
    ):
        super().__init__(app)
        self.logger = logging.getLogger(logger_name)
        self.include_trace = include_trace

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.perf_counter()
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # Build structured log entry
        log_entry = {
            "timestamp": time.time(),
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "query": str(request.url.query) if request.url.query else None,
            "client_ip": request.client.host if request.client else None,
        }

        try:
            response = await call_next(request)
        except Exception as e:
            duration = time.perf_counter() - start_time
            log_entry.update({
                "duration_ms": round(duration * 1000, 2),
                "status_code": 500,
                "error": str(e),
                "error_type": type(e).__name__,
            })
            if self.include_trace:
                import traceback
                log_entry["traceback"] = traceback.format_exc()
            self.logger.error("Request failed", extra=log_entry)
            raise

        duration = time.perf_counter() - start_time
        log_entry.update({
            "duration_ms": round(duration * 1000, 2),
            "status_code": response.status_code,
            "response_size": response.headers.get("content-length"),
        })

        # Log at appropriate level
        if response.status_code >= 500:
            self.logger.error("Request completed with error", extra=log_entry)
        elif response.status_code >= 400:
            self.logger.warning("Request completed with client error", extra=log_entry)
        else:
            self.logger.info("Request completed", extra=log_entry)

        response.headers["X-Request-ID"] = request_id
        return response