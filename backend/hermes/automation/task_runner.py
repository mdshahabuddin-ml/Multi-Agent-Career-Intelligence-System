"""
Task Runner - executes tasks with concurrency control and monitoring.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set

from ..core.task import Task, TaskResult, TaskStatus


class TaskRunner:
    """
    Executes tasks with controlled concurrency.

    Provides a managed execution environment with concurrency limits,
    task queuing, and execution monitoring.
    """

    def __init__(self, max_concurrent: int = 5):
        self._max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._running: Dict[str, asyncio.Task] = {}
        self._completed: List[TaskResult] = []
        self._handlers: Dict[str, Callable] = {}

    def register_handler(self, task_type: str, handler: Callable) -> None:
        """Register a handler function for a task type."""
        self._handlers[task_type] = handler

    async def submit(
        self,
        task: Task,
        handler: Optional[Callable] = None,
    ) -> TaskResult:
        """
        Submit a task for execution.

        Args:
            task: The task to execute.
            handler: Optional override for the registered handler.

        Returns:
            The TaskResult after execution completes.
        """
        if handler is None:
            handler = self._handlers.get(task.type)
        if handler is None:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"No handler registered for task type '{task.type}'",
            )

        async with self._semaphore:
            task.start()
            try:
                result = await handler(task)
                task.complete(result.output if hasattr(result, "output") else result)
                if isinstance(result, TaskResult):
                    self._completed.append(result)
                    return result
                result_obj = TaskResult(
                    task_id=task.id,
                    success=True,
                    output=result,
                )
                self._completed.append(result_obj)
                return result_obj
            except Exception as exc:
                task.fail(str(exc))
                result_obj = TaskResult(
                    task_id=task.id,
                    success=False,
                    error=str(exc),
                )
                self._completed.append(result_obj)
                return result_obj

    async def submit_batch(
        self,
        tasks: List[Task],
        handler: Optional[Callable] = None,
    ) -> List[TaskResult]:
        """Submit multiple tasks for concurrent execution."""
        coros = [self.submit(task, handler) for task in tasks]
        return list(await asyncio.gather(*coros, return_exceptions=False))

    async def cancel(self, task_id: str) -> bool:
        """Cancel a running task. Returns True if cancelled."""
        async_task = self._running.get(task_id)
        if async_task and not async_task.done():
            async_task.cancel()
            return True
        return False

    def get_stats(self) -> Dict[str, Any]:
        """Get execution statistics."""
        total = len(self._completed)
        successful = sum(1 for r in self._completed if r.success)
        return {
            "total_completed": total,
            "successful": successful,
            "failed": total - successful,
            "currently_running": len(self._running),
            "max_concurrent": self._max_concurrent,
        }

    def get_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent task execution history."""
        return [
            r.to_dict() for r in self._completed[-limit:]
        ]
