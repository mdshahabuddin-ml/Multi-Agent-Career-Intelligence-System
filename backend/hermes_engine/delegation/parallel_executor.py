"""
Parallel Executor - Executes multiple tasks concurrently.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class ParallelExecutor:
    """
    Executes multiple tasks with controlled concurrency.
    """

    def __init__(self, max_concurrent: int = 5):
        self._max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._running: Dict[str, asyncio.Task] = {}

    async def execute(
        self,
        tasks: List[Dict[str, Any]],
        handler: Callable,
    ) -> List[Dict[str, Any]]:
        """
        Execute multiple tasks concurrently.
        
        Args:
            tasks: List of task dictionaries
            handler: Async handler function
            
        Returns:
            List of results
        """
        coros = [
            self._execute_with_semaphore(task, handler)
            for task in tasks
        ]
        return list(await asyncio.gather(*coros, return_exceptions=False))

    async def _execute_with_semaphore(
        self,
        task: Dict[str, Any],
        handler: Callable,
    ) -> Dict[str, Any]:
        """Execute a task with concurrency control."""
        async with self._semaphore:
            task_id = task.get("id", str(id(task)))
            try:
                result = await handler(task)
                return {
                    "task_id": task_id,
                    "success": True,
                    "result": result,
                }
            except Exception as e:
                logger.error(f"Task {task_id} failed: {e}")
                return {
                    "task_id": task_id,
                    "success": False,
                    "error": str(e),
                }

    def get_stats(self) -> Dict[str, Any]:
        """Get execution statistics."""
        return {
            "max_concurrent": self._max_concurrent,
            "currently_running": len(self._running),
        }
