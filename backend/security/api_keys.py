"""API Key management."""

import hashlib
import secrets
import time
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

from fastapi import Depends, Request, HTTPException, status
from sqlalchemy.orm import Session

from backend.models import User
from backend.database import get_db
from backend.security.config import get_security_config


class APIKeyScope(Enum):
    """API key scopes."""
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"
    RESEARCH = "research"
    JOBS = "jobs"
    RESUME = "resume"


@dataclass
class APIKey:
    """API Key data."""
    id: str
    user_id: int
    name: str
    prefix: str
    hashed_key: str
    scopes: List[str]
    created_at: datetime
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    is_active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


class APIKeyManager:
    """Manages API keys for users."""

    def __init__(self, config=None):
        self.config = config or get_security_config()

    def generate_key(self) -> tuple[str, str]:
        """Generate a new API key. Returns (raw_key, prefix)."""
        raw_key = secrets.token_urlsafe(self.config.API_KEY_LENGTH)
        prefix = self.config.API_KEY_PREFIX
        return f"{prefix}{raw_key}", prefix

    def hash_key(self, raw_key: str) -> str:
        """Hash an API key for storage."""
        algorithm = self.config.API_KEY_HASH_ALGORITHM
        if algorithm == "sha256":
            return hashlib.sha256(raw_key.encode()).hexdigest()
        elif algorithm == "sha512":
            return hashlib.sha512(raw_key.encode()).hexdigest()
        else:
            raise ValueError(f"Unsupported hash algorithm: {algorithm}")

    def verify_key(self, raw_key: str, hashed_key: str) -> bool:
        """Verify an API key against its hash."""
        return self.hash_key(raw_key) == hashed_key

    def create_api_key(
        self,
        db: Session,
        user_id: int,
        name: str,
        scopes: List[str] = None,
        expires_in_days: int = None,
        metadata: Dict[str, Any] = None
    ) -> tuple[APIKey, str]:
        """Create a new API key for a user."""
        # Validate user exists
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("User not found")

        # Generate key
        raw_key, prefix = self.generate_key()
        hashed_key = self.hash_key(raw_key)

        # Default scopes
        if scopes is None:
            scopes = [APIKeyScope.READ.value]

        # Expiration
        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

        # Create API key record
        # In production, this would be a database model
        # For now, we'll store in a simple format
        api_key = APIKey(
            id=secrets.token_urlsafe(16),
            user_id=user_id,
            name=name,
            prefix=prefix,
            hashed_key=hashed_key,
            scopes=scopes,
            created_at=datetime.utcnow(),
            expires_at=expires_at,
            metadata=metadata or {},
        )

        # Store in database (would use a model)
        # For now, return the key
        return api_key, raw_key

    def validate_api_key(self, db: Session, raw_key: str) -> Optional[APIKey]:
        """Validate an API key and return its data."""
        if not raw_key or not raw_key.startswith(self.config.API_KEY_PREFIX):
            return None

        # Extract prefix and key part
        key_part = raw_key[len(self.config.API_KEY_PREFIX):]
        hashed_key = self.hash_key(key_part)

        # In production, query database for matching hash
        # For now, return None (would implement with APIKey model)
        return None

    def list_user_keys(self, db: Session, user_id: int) -> List[APIKey]:
        """List all API keys for a user."""
        # In production, query database
        return []

    def revoke_key(self, db: Session, key_id: str, user_id: int) -> bool:
        """Revoke an API key."""
        # In production, update database
        return True

    def update_key_scopes(self, db: Session, key_id: str, user_id: int, scopes: List[str]) -> bool:
        """Update API key scopes."""
        # In production, update database
        return True

    def rotate_key(self, db: Session, key_id: str, user_id: int) -> tuple[APIKey, str]:
        """Rotate an API key (create new, revoke old)."""
        # In production, would revoke old and create new
        return self.create_api_key(db, user_id, "rotated_key")


class APIKeyAuth:
    """API Key authentication dependency."""

    def __init__(self, required_scopes: List[str] = None):
        self.required_scopes = required_scopes or []
        self.manager = APIKeyManager()

    async def __call__(self, request: Request, db: Session = Depends(get_db)) -> User:
        """Authenticate request using API key."""
        from fastapi import Depends, HTTPException, status
        from backend.dependencies import get_db

        # Check Authorization header
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            api_key = auth_header[7:]  # Remove "Bearer "
        else:
            # Check X-API-Key header
            api_key = request.headers.get("X-API-Key")

        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key required",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Validate key
        key_data = self.manager.validate_api_key(db, api_key)
        if not key_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check expiration
        if key_data.expires_at and key_data.expires_at < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key expired",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check if active
        if not key_data.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key revoked",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check scopes
        if self.required_scopes:
            if not all(scope in key_data.scopes for scope in self.required_scopes):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient API key scopes",
                )

        # Update last used
        # key_data.last_used_at = datetime.utcnow()
        # db.commit()

        # Get user
        user = db.query(User).filter(User.id == key_data.user_id).first()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
            )

        # Attach API key info to request state
        request.state.api_key = key_data

        return user


# Dependency for requiring specific scopes
def require_scopes(*scopes: str):
    """Create dependency requiring specific API key scopes."""
    return APIKeyAuth(list(scopes))