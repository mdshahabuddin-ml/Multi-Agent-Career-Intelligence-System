"""
Browser Session - Manages browser sessions.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional


class BrowserSession:
    """
    Manages a browser session.
    """

    def __init__(self, session_id: Optional[str] = None):
        import uuid
        self.session_id = session_id or str(uuid.uuid4())
        self.created_at = datetime.utcnow()
        self._cookies: Dict[str, str] = {}
        self._headers: Dict[str, str] = {}

    def set_cookie(self, name: str, value: str) -> None:
        """Set a cookie."""
        self._cookies[name] = value

    def get_cookie(self, name: str) -> Optional[str]:
        """Get a cookie."""
        return self._cookies.get(name)

    def set_header(self, name: str, value: str) -> None:
        """Set a header."""
        self._headers[name] = value

    def get_headers(self) -> Dict[str, str]:
        """Get all headers."""
        return dict(self._headers)

    def clear(self) -> None:
        """Clear session data."""
        self._cookies.clear()
        self._headers.clear()
