"""
Human-in-Loop - Human oversight interface.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


class HumanInLoop:
    """
    Interface for human oversight of agent actions.
    """

    def __init__(self):
        self._approval_callback: Optional[Callable] = None
        self._pending: Dict[str, Dict[str, Any]] = {}

    def set_approval_callback(self, callback: Callable) -> None:
        """Set callback for approval requests."""
        self._approval_callback = callback

    async def request_approval(
        self,
        action: str,
        details: Dict[str, Any],
        timeout_seconds: int = 300,
    ) -> bool:
        """Request human approval."""
        import uuid
        request_id = str(uuid.uuid4())

        self._pending[request_id] = {
            "action": action,
            "details": details,
            "status": "pending",
        }

        if self._approval_callback:
            try:
                result = await self._approval_callback(request_id, action, details)
                self._pending[request_id]["status"] = "approved" if result else "rejected"
                return result
            except Exception as e:
                logger.error(f"Approval callback failed: {e}")
                self._pending[request_id]["status"] = "rejected"
                return False

        # Default: approve
        self._pending[request_id]["status"] = "approved"
        return True

    def get_pending(self) -> Dict[str, Dict[str, Any]]:
        """Get pending approval requests."""
        return dict(self._pending)
