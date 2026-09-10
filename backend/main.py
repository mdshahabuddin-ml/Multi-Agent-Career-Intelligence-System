from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.api import auth, health, resume, jobs, research, career, applications, interview, evaluation, security, data_pipeline, personalization, organization, monitoring, admin, rate_limits, content_calendar, notifications, profile, dashboard
from backend.api import hermes, memory, skills, automation, gateway, content, social
from backend.api import career_content, content_analytics, hermes_optimization
from backend.security import (
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    RequestValidationMiddleware,
    CSRFProtectionMiddleware,
)
from backend.middleware.logging_middleware import RequestLoggingMiddleware, StructuredLoggingMiddleware
from backend.security.config import get_security_config

app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "Multi-Agent Career Intelligence System "
        "with Research, RAG, Job Intelligence, "
        "Career Intelligence and Interview Intelligence."
    ),
    version="0.1.0",
)

# ==========================================
# Security Middleware (order matters - inner to outer)
# ==========================================
security_config = get_security_config()

# Request logging (outermost for logging - logs everything)
app.add_middleware(
    RequestLoggingMiddleware,
    log_requests=security_config.LOG_REQUESTS,
    log_responses=security_config.LOG_RESPONSES,
    log_request_body=security_config.LOG_REQUEST_BODY,
    log_response_body=security_config.LOG_RESPONSE_BODY,
    excluded_paths=set(security_config.LOG_EXCLUDED_PATHS),
    max_body_length=security_config.LOG_MAX_BODY_LENGTH,
)

# Structured logging for log aggregation
app.add_middleware(StructuredLoggingMiddleware)

# Request validation (innermost - validates before processing)
app.add_middleware(RequestValidationMiddleware, config=security_config)

# CSRF protection
app.add_middleware(CSRFProtectionMiddleware, config=security_config)

# Rate limiting
app.add_middleware(RateLimitMiddleware, config=security_config)

# Security headers (outermost - applied to all responses)
app.add_middleware(SecurityHeadersMiddleware, config=security_config)


# ==========================================
# CORS
# ==========================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=security_config.CORS_ALLOW_ORIGINS,
    allow_credentials=security_config.CORS_ALLOW_CREDENTIALS,
    allow_methods=security_config.CORS_ALLOW_METHODS,
    allow_headers=security_config.CORS_ALLOW_HEADERS,
)


# ==========================================
# Include API Routers
# ==========================================
app.include_router(auth.router, prefix="/api")
app.include_router(profile.router, prefix="/api")
app.include_router(health.router, prefix="/api")
app.include_router(resume.router, prefix="/api")
app.include_router(jobs.router, prefix="/api")
app.include_router(research.router, prefix="/api")
app.include_router(career.router, prefix="/api")
app.include_router(applications.router, prefix="/api")
app.include_router(interview.router, prefix="/api")
app.include_router(evaluation.router, prefix="/api")
app.include_router(security.router, prefix="/api")
app.include_router(data_pipeline.router, prefix="/api")
app.include_router(personalization.router, prefix="/api")
app.include_router(organization.router, prefix="/api")
app.include_router(monitoring.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(content_calendar.router, prefix="/api")
app.include_router(notifications.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(hermes.router, prefix="/api")
app.include_router(memory.router, prefix="/api")
app.include_router(skills.router, prefix="/api")
app.include_router(automation.router, prefix="/api")
app.include_router(gateway.router, prefix="/api")
app.include_router(content.router, prefix="/api")
app.include_router(social.router, prefix="/api")
app.include_router(career_content.router, prefix="/api")
app.include_router(content_analytics.router, prefix="/api")
app.include_router(hermes_optimization.router, prefix="/api")


# ==========================================
# Root Endpoint
# ==========================================
@app.get("/")
async def root():
    return {
        "application": settings.APP_NAME,
        "version": "0.1.0",
        "status": "running",
        "message": "CareerIntel AI backend is running.",
    }