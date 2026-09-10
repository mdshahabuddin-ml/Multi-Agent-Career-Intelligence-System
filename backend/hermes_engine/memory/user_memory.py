"""
User Memory - Manages user-specific memories.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class UserMemory:
    """
    Manages user-specific memories and preferences.
    """

    def __init__(self):
        self._user_data: Dict[str, Dict[str, Any]] = {}

    def store(
        self,
        user_id: str,
        key: str,
        value: Any,
        category: str = "preferences",
    ) -> None:
        """Store a user memory."""
        if user_id not in self._user_data:
            self._user_data[user_id] = {}

        self._user_data[user_id][key] = {
            "value": value,
            "category": category,
        }

    def retrieve(
        self,
        user_id: str,
        key: str,
        default: Any = None,
    ) -> Any:
        """Retrieve a user memory."""
        user_data = self._user_data.get(user_id, {})
        entry = user_data.get(key)
        return entry["value"] if entry else default

    def get_all(
        self,
        user_id: str,
        category: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get all memories for a user."""
        user_data = self._user_data.get(user_id, {})

        if category:
            return {
                k: v["value"]
                for k, v in user_data.items()
                if v.get("category") == category
            }

        return {k: v["value"] for k, v in user_data.items()}

    def delete(self, user_id: str, key: str) -> bool:
        """Delete a user memory."""
        user_data = self._user_data.get(user_id, {})
        if key in user_data:
            del user_data[key]
            return True
        return False

    def clear(self, user_id: str) -> None:
        """Clear all memories for a user."""
        self._user_data.pop(user_id, None)
