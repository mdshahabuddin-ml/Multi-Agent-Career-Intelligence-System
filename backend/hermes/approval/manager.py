"""
Approval Manager - handles human-in-the-loop approval workflows.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ApprovalRequest:
    """Represents a pending approval request."""

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

    Tracks pending approval requests and handles approval/rejection
    decisions with optional callbacks.
    """

    def __init__(self) -> None:
        self._requests: Dict[str, ApprovalRequest] = {}
        self._callbacks: Dict[str, Callable] = {}

    def request_approval(
        self,
        action: str,
        description: str,
        requester_id: str,
        data: Optional[Dict[str, Any]] = None,
        callback: Optional[Callable] = None,
        timeout_seconds: int = 300,
    ) -> ApprovalRequest:
        """
        Create a new approval request.

        Args:
            action: The action requiring approval.
            description: Human-readable description.
            requester_id: ID of the agent requesting approval.
            data: Optional data associated with the request.
            callback: Optional callback for when decision is made.
            timeout_seconds: Seconds before request expires.

        Returns:
            The created ApprovalRequest.
        """
        request = ApprovalRequest(
            action=action,
            description=description,
            requester_id=requester_id,
            data=data,
            timeout_seconds=timeout_seconds,
        )
        self._requests[request.id] = request
        if callback:
            self._callbacks[request.id] = callback
        return request

    def approve(
        self, request_id: str, notes: str = ""
    ) -> Optional[ApprovalRequest]:
        """Approve a pending request."""
        request = self._requests.get(request_id)
        if not request or request.status != ApprovalStatus.PENDING:
            return None

        request.status = ApprovalStatus.APPROVED
        request.decided_at = datetime.utcnow()
        request.decision_notes = notes
        self._trigger_callback(request)
        return request

    def reject(
        self, request_id: str, notes: str = ""
    ) -> Optional[ApprovalRequest]:
        """Reject a pending request."""
        request = self._requests.get(request_id)
        if not request or request.status != ApprovalStatus.PENDING:
            return None

        request.status = ApprovalStatus.REJECTED
        request.decided_at = datetime.utcnow()
        request.decision_notes = notes
        self._trigger_callback(request)
        return request

    def get_request(
        self, request_id: str
    ) -> Optional[ApprovalRequest]:
        """Get an approval request by ID."""
        return self._requests.get(request_id)

    def get_pending(self) -> List[ApprovalRequest]:
        """Get all pending approval requests."""
        return [
            r for r in self._requests.values()
            if r.status == ApprovalStatus.PENDING
        ]

    def get_all(self) -> List[Dict[str, Any]]:
        """Get all approval requests as dictionaries."""
        return [
            {
                "id": r.id,
                "action": r.action,
                "description": r.description,
                "requester_id": r.requester_id,
                "status": r.status.value,
                "created_at": r.created_at.isoformat(),
                "decided_at": r.decided_at.isoformat() if r.decided_at else None,
                "decision_notes": r.decision_notes,
            }
            for r in self._requests.values()
        ]

    def _trigger_callback(self, request: ApprovalRequest) -> None:
        """Trigger the callback for a decided request."""
        callback = self._callbacks.pop(request.id, None)
        if callback:
            try:
                callback(request)
            except Exception:
                pass
