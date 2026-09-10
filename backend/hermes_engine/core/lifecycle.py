"""
Task lifecycle - explicit execution state machine for Hermes tasks.

Centralizes the PENDING -> IN_PROGRESS -> COMPLETED / FAILED / CANCELLED
transitions that were previously scattered (and partly unenforced) across
agents and the supervisor. Illegal transitions raise TransitionError instead
of silently corrupting task state.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Awaitable, Callable, Dict, Optional

from .task import HermesTask

logger = logging.getLogger(__name__)


class TransitionError(ValueError):
    """Raised when a task lifecycle transition is not allowed."""


# Allowed transitions between HermesTask.status values.
_ALLOWED_TRANSITIONS: Dict[str, frozenset] = {
    "pending": frozenset({"in_progress", "cancelled"}),
    "in_progress": frozenset({"completed", "failed", "cancelled"}),
    "completed": frozenset(),
    "failed": frozenset(),
    "cancelled": frozenset(),
}

TERMINAL_STATUSES = frozenset({"completed", "failed", "cancelled"})


def is_terminal(task: HermesTask) -> bool:
    """Check whether a task is in a terminal state."""
    return task.status in TERMINAL_STATUSES


def transition(task: HermesTask, to_status: str) -> HermesTask:
    """
    Move a task to a new status, enforcing the lifecycle state machine.

    No-op when the task is already in the requested status.
    Raises TransitionError for illegal transitions (e.g. completing a
    task that never started, or restarting a completed task).
    """
    if task.status == to_status:
        return task
    allowed = _ALLOWED_TRANSITIONS.get(task.status, frozenset())
    if to_status not in allowed:
        raise TransitionError(
            f"Illegal task transition: {task.status!r} -> {to_status!r} "
            f"(task {task.id})"
        )
    if to_status == "in_progress":
        task.start()
    elif to_status == "completed":
        task.complete()
    elif to_status == "failed":
        task.fail(task.metadata.get("error", ""))
    elif to_status == "cancelled":
        task.cancel()
    return task


def begin(task: HermesTask) -> HermesTask:
    """Mark a task as started (pending -> in_progress)."""
    return transition(task, "in_progress")


def succeed(task: HermesTask, output: Any = None) -> HermesTask:
    """Mark a task as completed (in_progress -> completed)."""
    if output is not None:
        task.metadata["output"] = output
    return transition(task, "completed")


def fail(task: HermesTask, error: str = "") -> HermesTask:
    """Mark a task as failed (in_progress -> failed)."""
    if error:
        task.metadata["error"] = error
    else:
        task.metadata.setdefault("error", "Unknown error")
    return transition(task, "failed")


def cancel(task: HermesTask) -> HermesTask:
    """Mark a task as cancelled (pending/in_progress -> cancelled)."""
    return transition(task, "cancelled")


async def run_with_lifecycle(
    task: HermesTask,
    handler: Callable[[], Awaitable[Any]],
    timeout: Optional[float] = None,
) -> Any:
    """
    Drive a task through its lifecycle around an async handler.

    - Marks the task started before invoking the handler.
    - Enforces ``timeout`` seconds via asyncio.wait_for when given.
    - Marks completed/failed/cancelled appropriately and re-raises
      cancellations and unexpected errors to the caller.

    Returns whatever the handler returns.
    """
    begin(task)
    try:
        if timeout:
            result = await asyncio.wait_for(handler(), timeout=timeout)
        else:
            result = await handler()
    except asyncio.CancelledError:
        cancel(task)
        raise
    except asyncio.TimeoutError as exc:
        fail(task, f"Task timed out after {timeout} seconds")
        raise TimeoutError(f"Task {task.id} timed out after {timeout} seconds") from exc
    except Exception as exc:
        fail(task, str(exc))
        raise
    succeed(task, result)
    return result
