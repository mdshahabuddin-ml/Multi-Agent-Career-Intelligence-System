"""Security middleware for FastAPI."""

import time
import hashlib
import secrets
from typing import Callable, Optional, Set
from collections import defaultdict

from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from backend.security.config import get_security_config
from backend.utils.security import decode_token


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware using sliding window."""

    def __init__(self, app: ASGIApp, config=None):
        super().__init__(app)
        self.config = config or get_security_config()
        self.requests: defaultdict[str, list] = defaultdict(list)
        self.blocked_ips: dict[str, float] = {}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not self.config.RATE_LIMIT_ENABLED:
            return await call_next(request)

        # Get client IP
        client_ip = self._get_client_ip(request)

        # Check if IP is blocked
        if client_ip in self.blocked_ips:
            if time.time() < self.blocked_ips[client_ip]:
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={"detail": "Too many requests. IP temporarily blocked."},
                    headers={"Retry-After": str(int(self.blocked_ips[client_ip] - time.time()))}
                )
            else:
                del self.blocked_ips[client_ip]

        # Check IP blacklist/whitelist
        if self.config.IP_BLACKLIST and client_ip in self.config.IP_BLACKLIST:
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "Access denied"}
            )

        if self.config.IP_WHITELIST and client_ip not in self.config.IP_WHITELIST:
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "Access denied"}
            )

        # Clean old requests
        current_time = time.time()
        window_start = current_time - self.config.RATE_LIMIT_WINDOW_SECONDS

        # Remove old entries
        self.requests[client_ip] = [
            req_time for req_time in self.requests[client_ip]
            if req_time > window_start
        ]

        # Check rate limit
        if len(self.requests[client_ip]) >= self.config.RATE_LIMIT_REQUESTS:
            # Check burst
            recent_requests = [
                req_time for req_time in self.requests[client_ip]
                if req_time > current_time - 10  # Last 10 seconds
            ]
            if len(recent_requests) >= self.config.RATE_LIMIT_BURST:
                # Block IP temporarily
                self.blocked_ips[client_ip] = current_time + self.config.LOCKOUT_DURATION_MINUTES * 60
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={"detail": "Rate limit exceeded. IP temporarily blocked."},
                    headers={"Retry-After": str(self.config.LOCKOUT_DURATION_MINUTES * 60)}
                )

        # Add current request
        self.requests[client_ip].append(current_time)

        # Add rate limit headers
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.config.RATE_LIMIT_REQUESTS)
        response.headers["X-RateLimit-Remaining"] = str(
            max(0, self.config.RATE_LIMIT_REQUESTS - len(self.requests[client_ip]))
        )
        response.headers["X-RateLimit-Reset"] = str(int(current_time + self.config.RATE_LIMIT_WINDOW_SECONDS))

        return response

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request."""
        # Check X-Forwarded-For header (for proxied requests)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        # Check X-Real-IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Fall back to client host
        return request.client.host if request.client else "unknown"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Security headers middleware."""

    def __init__(self, app: ASGIApp, config=None):
        super().__init__(app)
        self.config = config or get_security_config()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        if not self.config.SECURITY_HEADERS_ENABLED:
            return response

        # HSTS
        response.headers["Strict-Transport-Security"] = (
            f"max-age={self.config.HSTS_MAX_AGE}; includeSubDomains; preload"
        )

        # CSP
        response.headers["Content-Security-Policy"] = self.config.CSP_POLICY

        # X-Frame-Options
        response.headers["X-Frame-Options"] = self.config.X_FRAME_OPTIONS

        # X-Content-Type-Options
        response.headers["X-Content-Type-Options"] = self.config.X_CONTENT_TYPE_OPTIONS

        # Referrer-Policy
        response.headers["Referrer-Policy"] = self.config.REFERRER_POLICY

        # Permissions-Policy
        response.headers["Permissions-Policy"] = self.config.PERMISSIONS_POLICY

        # X-XSS-Protection (legacy but still useful)
        if self.config.ENABLE_XSS_PROTECTION:
            response.headers["X-XSS-Protection"] = "1; mode=block"

        # Remove server header
        if "Server" in response.headers:
            del response.headers["Server"]

        return response


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """Request validation middleware."""

    def __init__(self, app: ASGIApp, config=None):
        super().__init__(app)
        self.config = config or get_security_config()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Check content length
        content_length = request.headers.get("Content-Length")
        if content_length:
            size_mb = int(content_length) / (1024 * 1024)
            if size_mb > self.config.MAX_REQUEST_SIZE_MB:
                return JSONResponse(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    content={"detail": f"Request too large. Max size: {self.config.MAX_REQUEST_SIZE_MB}MB"}
                )

        # Validate JSON depth for JSON requests
        if request.headers.get("Content-Type", "").startswith("application/json"):
            try:
                body = await request.body()
                if body:
                    import json
                    data = json.loads(body)
                    if self._get_json_depth(data) > self.config.MAX_JSON_DEPTH:
                        return JSONResponse(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            content={"detail": "JSON structure too deep"}
                        )
                    if self._get_array_length(data) > self.config.MAX_ARRAY_LENGTH:
                        return JSONResponse(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            content={"detail": "Array length exceeds maximum"}
                        )
            except json.JSONDecodeError:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"detail": "Invalid JSON"}
                )

        return await call_next(request)

    def _get_json_depth(self, obj, current_depth=0) -> int:
        """Calculate JSON nesting depth."""
        if current_depth > self.config.MAX_JSON_DEPTH:
            return current_depth

        if isinstance(obj, dict):
            if not obj:
                return current_depth
            return max(
                self._get_json_depth(v, current_depth + 1)
                for v in obj.values()
            )
        elif isinstance(obj, list):
            if not obj:
                return current_depth
            return max(
                self._get_json_depth(item, current_depth + 1)
                for item in obj
            )
        return current_depth

    def _get_array_length(self, obj) -> int:
        """Get maximum array length in JSON."""
        max_len = 0
        if isinstance(obj, list):
            max_len = len(obj)
            for item in obj:
                max_len = max(max_len, self._get_array_length(item))
        elif isinstance(obj, dict):
            for v in obj.values():
                max_len = max(max_len, self._get_array_length(v))
        return max_len


class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    """CSRF protection middleware."""

    def __init__(self, app: ASGIApp, config=None):
        super().__init__(app)
        self.config = config or get_security_config()
        self.exempt_paths = {
            "/api/auth/login",
            "/api/auth/register",
            "/api/auth/me",
            "/health",
            "/docs",
            "/openapi.json",
            "/redoc",
        }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Disable CSRF in testing mode
        if self.config.TESTING or not self.config.ENABLE_CSRF_PROTECTION:
            return await call_next(request)

        # Skip for exempt paths
        if request.url.path in self.exempt_paths:
            return await call_next(request)

        # Skip for safe methods
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return await call_next(request)

        # Skip for API key authenticated requests
        if request.headers.get("X-API-Key"):
            return await call_next(request)

        # Check CSRF token
        csrf_token = request.headers.get(self.config.CSRF_HEADER_NAME)
        csrf_cookie = request.cookies.get(self.config.CSRF_COOKIE_NAME)

        if not csrf_token or not csrf_cookie or csrf_token != csrf_cookie:
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "CSRF token missing or invalid"}
            )

        return await call_next(request)


def generate_csrf_token() -> str:
    """Generate a CSRF token."""
    return secrets.token_urlsafe(32)