"""
Action Policy - Defines action policies.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class ActionPolicy:
    """
    Defines policies for agent actions.
    """

    def __init__(self):
        self._policies: Dict[str, Dict[str, Any]] = {}

    def add_policy(
        self,
        action: str,
        requires_approval: bool = False,
        allowed_roles: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Add a policy for an action."""
        self._policies[action] = {
            "requires_approval": requires_approval,
            "allowed_roles": allowed_roles or [],
            "metadata": metadata or {},
        }

    def check(
        self,
        action: str,
        user_role: str = "user",
    ) -> Dict[str, Any]:
        """Check if an action is allowed."""
        policy = self._policies.get(action)
        if not policy:
            return {"allowed": True, "requires_approval": False}

        allowed_roles = policy.get("allowed_roles", [])
        if allowed_roles and user_role not in allowed_roles:
            return {"allowed": False, "reason": "Insufficient permissions"}

        return {
            "allowed": True,
            "requires_approval": policy.get("requires_approval", False),
        }

    def list_policies(self) -> Dict[str, Any]:
        """List all policies."""
        return dict(self._policies)
