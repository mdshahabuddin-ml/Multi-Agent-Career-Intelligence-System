"""
Scheduler - Manages timed task execution.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional
import heapq


class ScheduledTask:
    """A scheduled task entry."""

    def __init__(
        self,
        task_id: str,
        handler: Callable,
        run_at: datetime,
        args: tuple = (),
        kwargs: Optional[Dict[str, Any]] = None,
        recurring: bool = False,
        interval_seconds: Optional[float] = None,
    ):
        self.task_id = task_id
        self.handler = handler
        self.run_at = run_at
        self.args = args
        self.kwargs = kwargs or {}
        self.recurring = recurring
        self.interval_seconds = interval_seconds
        self.executions = 0
        self.last_error: Optional[str] = None

    def __lt__(self, other: "ScheduledTask") -> bool:
        return self.run_at < other.run_at


class Scheduler:
    """
    Manages scheduled and recurring task execution.
    """

    def __init__(self) -> None:
        self._queue: List[ScheduledTask] = []
        self._tasks: Dict[str, ScheduledTask] = {}
        self._running = False
        self._task: Optional[asyncio.Task] = None

    def schedule(
        self,
        task_id: str,
        handler: Callable,
        run_at: datetime,
        args: tuple = (),
        kwargs: Optional[Dict[str, Any]] = None,
        recurring: bool = False,
        interval_seconds: Optional[float] = None,
    ) -> ScheduledTask:
        """Schedule a task."""
        scheduled = ScheduledTask(
            task_id=task_id,
            handler=handler,
            run_at=run_at,
            args=args,
            kwargs=kwargs,
            recurring=recurring,
            interval_seconds=interval_seconds,
        )
        heapq.heappush(self._queue, scheduled)
        self._tasks[task_id] = scheduled
        return scheduled

    def schedule_in(
        self,
        task_id: str,
        handler: Callable,
        delay_seconds: float,
        **kwargs: Any,
    ) -> ScheduledTask:
        """Schedule a task after a delay."""
        run_at = datetime.utcnow() + timedelta(seconds=delay_seconds)
        return self.schedule(task_id=task_id, handler=handler, run_at=run_at, kwargs=kwargs)

    def cancel(self, task_id: str) -> bool:
        """Cancel a scheduled task."""
        task = self._tasks.pop(task_id, None)
        if task and task in self._queue:
            self._queue.remove(task)
            heapq.heapify(self._queue)
            return True
        return False

    async def start(self) -> None:
        """Start the scheduler."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        """Stop the scheduler."""
        self._running = False
        if self._task:
            self._task.cancel()

    async def _run_loop(self) -> None:
        """Main scheduler loop."""
        while self._running:
            now = datetime.utcnow()
            while self._queue and self._queue[0].run_at <= now:
                scheduled = heapq.heappop(self._queue)
                try:
                    await scheduled.handler(*scheduled.args, **scheduled.kwargs)
                    scheduled.executions += 1
                    scheduled.last_error = None

                    if scheduled.recurring and scheduled.interval_seconds:
                        scheduled.run_at = now + timedelta(seconds=scheduled.interval_seconds)
                        heapq.heappush(self._queue, scheduled)
                except Exception as exc:
                    scheduled.last_error = str(exc)
                    if not scheduled.recurring:
                        self._tasks.pop(scheduled.task_id, None)

            await asyncio.sleep(0.1)

    def get_pending(self) -> List[Dict[str, Any]]:
        """Get pending scheduled tasks."""
        return [
            {
                "task_id": t.task_id,
                "run_at": t.run_at.isoformat(),
                "recurring": t.recurring,
                "executions": t.executions,
            }
            for t in sorted(self._queue)
        ]
