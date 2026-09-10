"""
Task Router - Routes tasks to appropriate handlers.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class TaskRouter:
    """
    Routes tasks to appropriate handlers based on task type.
    """

    def __init__(self):
        self._handlers: Dict[str, Callable] = {}
        self._fallback: Optional[Callable] = None

    def register(self, task_type: str, handler: Callable) -> None:
        """Register a handler for a task type."""
        self._handlers[task_type] = handler

    def set_fallback(self, handler: Callable) -> None:
        """Set a fallback handler."""
        self._fallback = handler

    async def route(self, task: Dict[str, Any]) -> Any:
        """
        Route a task to its handler.
        
        Args:
            task: Task dictionary with 'type' key
            
        Returns:
            Handler result
        """
        task_type = task.get("type", "generic")
        handler = self._handlers.get(task_type) or self._fallback

        if handler:
            return await handler(task)
        else:
            raise ValueError(f"No handler registered for task type: {task_type}")

    def get_handler(self, task_type: str) -> Optional[Callable]:
        """Get handler for a task type."""
        return self._handlers.get(task_type)

    def list_types(self) -> List[str]:
        """List registered task types."""
        return list(self._handlers.keys())
