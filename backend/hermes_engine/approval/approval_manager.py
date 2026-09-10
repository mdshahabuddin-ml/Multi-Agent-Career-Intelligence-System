"""
Approval Manager - Manages approval workflows.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
from enum import Enum


class ApprovalStatus(str, Enum):
    """Approval status."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ApprovalRequest:
    """An approval request."""

    def __init__(
        self,
        action: str,
        description: str,
        requester_id: str,
        data: Optional[Dict[str, Any]] = None,
        timeout_seconds: int = 300,
    ):
        self.id = str(uuid.uuid4())
        self.action = action
        self.description = description
        self.requester_id = requester_id
        self.data = data or {}
        self.status = ApprovalStatus.PENDING
        self.created_at = datetime.utcnow()
        self.timeout_seconds = timeout_seconds
        self.decided_at: Optional[datetime] = None
        self.decision_notes: str = ""


class ApprovalManager:
    """
    Manages human-in-the-loop approval workflows.
    """

    def __init__(self):
        self._requests: Dict[str, ApprovalRequest] = {}
        self._callbacks: Dict[str, Callable] = {}

    def request_approval(
        self,
        action: str,
        description: str,
        requester_id: str,
        data: Optional[Dict[str, Any]] = None,
        callback: Optional[Callable] = None,
    ) -> ApprovalRequest:
        """Create an approval request."""
        request = ApprovalRequest(
            action=action,
            description=description,
            requester_id=requester_id,
            data=data,
        )
        self._requests[request.id] = request
        if callback:
            self._callbacks[request.id] = callback
        return request

    def approve(self, request_id: str, notes: str = "") -> Optional[ApprovalRequest]:
        """Approve a request."""
        request = self._requests.get(request_id)
        if not request or request.status != ApprovalStatus.PENDING:
            return None

        request.status = ApprovalStatus.APPROVED
        request.decided_at = datetime.utcnow()
        request.decision_notes = notes
        self._trigger_callback(request)
        return request

    def reject(self, request_id: str, notes: str = "") -> Optional[ApprovalRequest]:
        """Reject a request."""
        request = self._requests.get(request_id)
        if not request or request.status != ApprovalStatus.PENDING:
            return None

        request.status = ApprovalStatus.REJECTED
        request.decided_at = datetime.utcnow()
        request.decision_notes = notes
        self._trigger_callback(request)
        return request

    def get_pending(self) -> List[Dict[str, Any]]:
        """Get pending requests."""
        return [
            {
                "id": r.id,
                "action": r.action,
                "description": r.description,
                "status": r.status.value,
                "created_at": r.created_at.isoformat(),
            }
            for r in self._requests.values()
            if r.status == ApprovalStatus.PENDING
        ]

    def _trigger_callback(self, request: ApprovalRequest) -> None:
        """Trigger callback for a decided request."""
        callback = self._callbacks.pop(request.id, None)
        if callback:
            try:
                callback(request)
            except Exception:
                pass
