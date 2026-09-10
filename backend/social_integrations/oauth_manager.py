"""
OAuth Manager - Manages OAuth flows.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


class OAuthManager:
    """Manages OAuth authentication flows."""

    def __init__(self):
        self._providers: Dict[str, Dict[str, Any]] = {}

    def register_provider(
        self,
        name: str,
        client_id: str,
        client_secret: str,
        auth_url: str,
        token_url: str,
    ) -> None:
        """Register an OAuth provider."""
        self._providers[name] = {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_url": auth_url,
            "token_url": token_url,
        }

    def get_auth_url(self, provider: str, redirect_uri: str) -> str:
        """Get authorization URL."""
        config = self._providers.get(provider)
        if not config:
            raise ValueError(f"Provider '{provider}' not registered")
        return f"{config['auth_url']}?client_id={config['client_id']}&redirect_uri={redirect_uri}"

    async def exchange_code(self, provider: str, code: str) -> Dict[str, Any]:
        """Exchange authorization code for token."""
        return {"access_token": "token", "expires_in": 3600}
