"""
Token Manager - Manages access tokens.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, Optional


class TokenManager:
    """Manages access tokens for social platforms."""

    def __init__(self):
        self._tokens: Dict[str, Dict[str, Any]] = {}

    def store(
        self,
        platform: str,
        user_id: str,
        access_token: str,
        refresh_token: Optional[str] = None,
        expires_in: int = 3600,
    ) -> None:
        """Store a token."""
        self._tokens[f"{platform}:{user_id}"] = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_at": (datetime.utcnow() + timedelta(seconds=expires_in)).isoformat(),
        }

    def get(self, platform: str, user_id: str) -> Optional[str]:
        """Get an access token."""
        entry = self._tokens.get(f"{platform}:{user_id}")
        if entry:
            return entry["access_token"]
        return None

    def is_expired(self, platform: str, user_id: str) -> bool:
        """Check if a token is expired."""
        entry = self._tokens.get(f"{platform}:{user_id}")
        if not entry:
            return True
        expires_at = datetime.fromisoformat(entry["expires_at"])
        return datetime.utcnow() > expires_at

    def revoke(self, platform: str, user_id: str) -> bool:
        """Revoke a token."""
        return self._tokens.pop(f"{platform}:{user_id}", None) is not None
