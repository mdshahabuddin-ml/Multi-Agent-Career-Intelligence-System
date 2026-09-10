"""Security API endpoints."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.api import auth
from backend.database import get_db
from backend.dependencies import get_current_active_user
from backend.models import User
from backend.security import (
    APIKeyManager,
    APIKeyScope,
    require_scopes,
    audit_logger,
    AuditEventType,
    AuditSeverity,
)

router = APIRouter(prefix="/security", tags=["Security"])


# ==========================================
# Schemas
# ==========================================

class APIKeyCreateRequest(BaseModel):
    """Request to create an API key."""
    name: str = Field(..., min_length=1, max_length=100, description="Name for the API key")
    scopes: List[str] = Field(default=["read"], description="List of scopes")
    expires_in_days: Optional[int] = Field(None, ge=1, le=365, description="Expiration in days")
    metadata: Optional[dict] = Field(None, description="Additional metadata")


class APIKeyResponse(BaseModel):
    """API Key response (without the raw key)."""
    id: str
    name: str
    prefix: str
    scopes: List[str]
    created_at: str
    expires_at: Optional[str]
    last_used_at: Optional[str]
    is_active: bool


class APIKeyCreateResponse(BaseModel):
    """Response when creating an API key (includes raw key)."""
    api_key: APIKeyResponse
    raw_key: str = Field(..., description="The raw API key - only shown once!")


class APIKeyUpdateRequest(BaseModel):
    """Request to update an API key."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    scopes: Optional[List[str]] = None
    is_active: Optional[bool] = None


class AvailableScopesResponse(BaseModel):
    """Available API key scopes."""
    scopes: List[dict]


# ==========================================
# Endpoints
# ==========================================

@router.get("/scopes", response_model=AvailableScopesResponse)
async def get_available_scopes(
    current_user: User = Depends(get_current_active_user),
):
    """Get available API key scopes."""
    return {
        "scopes": [
            {"value": scope.value, "description": scope.value.replace("_", " ").title()}
            for scope in APIKeyScope
        ]
    }


@router.post("/api-keys", response_model=APIKeyCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    request: APIKeyCreateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Create a new API key for the current user."""
    manager = APIKeyManager()

    # Validate scopes
    valid_scopes = [s.value for s in APIKeyScope]
    for scope in request.scopes:
        if scope not in valid_scopes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid scope: {scope}. Valid scopes: {valid_scopes}"
            )

    # Create API key
    api_key, raw_key = manager.create_api_key(
        db=db,
        user_id=current_user.id,
        name=request.name,
        scopes=request.scopes,
        expires_in_days=request.expires_in_days,
        metadata=request.metadata,
    )

    # Log audit event
    audit_logger.log_api_key_event(
        AuditEventType.API_KEY_CREATED,
        user_id=current_user.id,
        key_id=api_key.id,
        ip=current_user.id,  # Would get from request in real implementation
        name=request.name,
        scopes=request.scopes,
    )

    return APIKeyCreateResponse(
        api_key=APIKeyResponse(
            id=api_key.id,
            name=api_key.name,
            prefix=api_key.prefix,
            scopes=api_key.scopes,
            created_at=api_key.created_at.isoformat(),
            expires_at=api_key.expires_at.isoformat() if api_key.expires_at else None,
            last_used_at=api_key.last_used_at.isoformat() if api_key.last_used_at else None,
            is_active=api_key.is_active,
        ),
        raw_key=raw_key,
    )


@router.get("/api-keys", response_model=List[APIKeyResponse])
async def list_api_keys(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """List all API keys for the current user."""
    manager = APIKeyManager()
    keys = manager.list_user_keys(db, current_user.id)

    return [
        APIKeyResponse(
            id=k.id,
            name=k.name,
            prefix=k.prefix,
            scopes=k.scopes,
            created_at=k.created_at.isoformat(),
            expires_at=k.expires_at.isoformat() if k.expires_at else None,
            last_used_at=k.last_used_at.isoformat() if k.last_used_at else None,
            is_active=k.is_active,
        )
        for k in keys
    ]


@router.get("/api-keys/{key_id}", response_model=APIKeyResponse)
async def get_api_key(
    key_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get a specific API key (without raw key)."""
    manager = APIKeyManager()
    keys = manager.list_user_keys(db, current_user.id)

    key = next((k for k in keys if k.id == key_id), None)
    if not key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )

    return APIKeyResponse(
        id=key.id,
        name=key.name,
        prefix=key.prefix,
        scopes=key.scopes,
        created_at=key.created_at.isoformat(),
        expires_at=key.expires_at.isoformat() if key.expires_at else None,
        last_used_at=key.last_used_at.isoformat() if key.last_used_at else None,
        is_active=key.is_active,
    )


@router.patch("/api-keys/{key_id}", response_model=APIKeyResponse)
async def update_api_key(
    key_id: str,
    request: APIKeyUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update an API key."""
    manager = APIKeyManager()
    keys = manager.list_user_keys(db, current_user.id)

    key = next((k for k in keys if k.id == key_id), None)
    if not key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )

    # Validate scopes if provided
    if request.scopes is not None:
        valid_scopes = [s.value for s in APIKeyScope]
        for scope in request.scopes:
            if scope not in valid_scopes:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid scope: {scope}"
                )
        manager.update_key_scopes(db, key_id, current_user.id, request.scopes)
        key.scopes = request.scopes

    if request.name is not None:
        # Would update in DB
        key.name = request.name

    if request.is_active is not None:
        if not request.is_active:
            manager.revoke_key(db, key_id, current_user.id)
        key.is_active = request.is_active

    # Log audit event
    audit_logger.log_api_key_event(
        AuditEventType.API_KEY_ROTATED if request.scopes else AuditEventType.API_KEY_REVOKED,
        user_id=current_user.id,
        key_id=key_id,
        ip="",
        updates=request.dict(exclude_unset=True),
    )

    return APIKeyResponse(
        id=key.id,
        name=key.name,
        prefix=key.prefix,
        scopes=key.scopes,
        created_at=key.created_at.isoformat(),
        expires_at=key.expires_at.isoformat() if key.expires_at else None,
        last_used_at=key.last_used_at.isoformat() if key.last_used_at else None,
        is_active=key.is_active,
    )


@router.delete("/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    key_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Revoke an API key."""
    manager = APIKeyManager()
    keys = manager.list_user_keys(db, current_user.id)

    key = next((k for k in keys if k.id == key_id), None)
    if not key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )

    manager.revoke_key(db, key_id, current_user.id)

    # Log audit event
    audit_logger.log_api_key_event(
        AuditEventType.API_KEY_REVOKED,
        user_id=current_user.id,
        key_id=key_id,
        ip="",
    )


@router.post("/api-keys/{key_id}/rotate", response_model=APIKeyCreateResponse, status_code=status.HTTP_201_CREATED)
async def rotate_api_key(
    key_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Rotate an API key (create new, revoke old)."""
    manager = APIKeyManager()
    keys = manager.list_user_keys(db, current_user.id)

    key = next((k for k in keys if k.id == key_id), None)
    if not key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )

    # Create new key with same settings
    new_key, raw_key = manager.rotate_key(db, key_id, current_user.id)

    # Log audit event
    audit_logger.log_api_key_event(
        AuditEventType.API_KEY_ROTATED,
        user_id=current_user.id,
        key_id=key_id,
        ip="",
        new_key_id=new_key.id,
    )

    return APIKeyCreateResponse(
        api_key=APIKeyResponse(
            id=new_key.id,
            name=new_key.name,
            prefix=new_key.prefix,
            scopes=new_key.scopes,
            created_at=new_key.created_at.isoformat(),
            expires_at=new_key.expires_at.isoformat() if new_key.expires_at else None,
            last_used_at=new_key.last_used_at.isoformat() if new_key.last_used_at else None,
            is_active=new_key.is_active,
        ),
        raw_key=raw_key,
    )


# ==========================================
# Security Status
# ==========================================

class SecurityStatusResponse(BaseModel):
    """Security status response."""
    rate_limiting: dict
    security_headers: dict
    cors: dict
    api_keys: dict
    audit_logging: bool


@router.get("/status", response_model=SecurityStatusResponse)
async def get_security_status(
    current_user: User = Depends(require_scopes("admin")),
):
    """Get security configuration status (admin only)."""
    from backend.security.config import get_security_config

    config = get_security_config()

    return SecurityStatusResponse(
        rate_limiting={
            "enabled": config.RATE_LIMIT_ENABLED,
            "requests_per_window": config.RATE_LIMIT_REQUESTS,
            "window_seconds": config.RATE_LIMIT_WINDOW_SECONDS,
            "burst_limit": config.RATE_LIMIT_BURST,
        },
        security_headers={
            "enabled": config.SECURITY_HEADERS_ENABLED,
            "hsts_max_age": config.HSTS_MAX_AGE,
            "csp_policy": config.CSP_POLICY[:100] + "..." if len(config.CSP_POLICY) > 100 else config.CSP_POLICY,
        },
        cors={
            "allowed_origins": config.CORS_ALLOW_ORIGINS,
            "allow_credentials": config.CORS_ALLOW_CREDENTIALS,
        },
        api_keys={
            "enabled": config.API_KEY_ENABLED,
            "prefix": config.API_KEY_PREFIX,
        },
        audit_logging=config.AUDIT_LOG_ENABLED,
    )


# ==========================================
# CSRF Token
# ==========================================

class CSRFTokenResponse(BaseModel):
    """CSRF token response."""
    csrf_token: str


@router.get("/csrf-token", response_model=CSRFTokenResponse)
async def get_csrf_token(response: Response):
    """Get a CSRF token for form submissions (public endpoint)."""
    from backend.security.middleware import generate_csrf_token
    from backend.security.config import get_security_config

    token = generate_csrf_token()
    config = get_security_config()

    # Set CSRF token as cookie
    response.set_cookie(
        key=config.CSRF_COOKIE_NAME,
        value=token,
        httponly=False,
        secure=False,  # Set to True in production with HTTPS
        samesite="lax",
        max_age=3600,  # 1 hour
        path="/",
    )

    return CSRFTokenResponse(csrf_token=token)