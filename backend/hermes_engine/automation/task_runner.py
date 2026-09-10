"""
Task Runner - Executes tasks with concurrency control.
"""

from __future__ import annotations

import asyncio
from typing import Any, Callable, Dict, List, Optional


class TaskRunner:
    """
    Executes tasks with controlled concurrency.
    """

    def __init__(self, max_concurrent: int = 5):
        self._max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._handlers: Dict[str, Callable] = {}
        self._completed: List[Dict[str, Any]] = []

    def register_handler(self, task_type: str, handler: Callable) -> None:
        """Register a handler for a task type."""
        self._handlers[task_type] = handler

    async def submit(
        self,
        task: Dict[str, Any],
        handler: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        """Submit a task for execution."""
        if handler is None:
            handler = self._handlers.get(task.get("type", "generic"))
        if handler is None:
            return {
                "success": False,
                "error": f"No handler for task type '{task.get('type')}'",
            }

        async with self._semaphore:
            try:
                result = await handler(task)
                self._completed.append({"task": task, "success": True})
                return {"success": True, "result": result}
            except Exception as e:
                self._completed.append({"task": task, "success": False, "error": str(e)})
                return {"success": False, "error": str(e)}

    async def submit_batch(
        self,
        tasks: List[Dict[str, Any]],
        handler: Optional[Callable] = None,
    ) -> List[Dict[str, Any]]:
        """Submit multiple tasks."""
        coros = [self.submit(task, handler) for task in tasks]
        return list(await asyncio.gather(*coros))

    def get_stats(self) -> Dict[str, Any]:
        """Get execution statistics."""
        total = len(self._completed)
        successful = sum(1 for r in self._completed if r.get("success"))
        return {
            "total": total,
            "successful": successful,
            "failed": total - successful,
            "max_concurrent": self._max_concurrent,
        }
