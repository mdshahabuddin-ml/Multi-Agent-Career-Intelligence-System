"""
Skill Executor - handles skill execution with timeout and error handling.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Callable, Dict, Optional


class SkillExecutor:
    """
    Executes skill handlers with safety measures.

    Provides timeout enforcement, error handling, and
    execution statistics tracking.
    """

    def __init__(self) -> None:
        self._total_executions = 0
        self._total_errors = 0
        self._total_duration_ms = 0.0

    async def execute(
        self,
        handler: Callable,
        params: Dict[str, Any],
        timeout: Optional[float] = None,
    ) -> Any:
        """
        Execute a skill handler with timeout protection.

        Args:
            handler: The async callable to execute.
            params: Parameters to pass to the handler.
            timeout: Optional timeout in seconds. None means no timeout.

        Returns:
            The result of the handler execution.

        Raises:
            TimeoutError: If execution exceeds the timeout.
            Exception: Any exception raised by the handler.
        """
        start = time.monotonic()
        self._total_executions += 1

        try:
            if timeout:
                result = await asyncio.wait_for(
                    handler(**params),
                    timeout=timeout,
                )
            else:
                result = await handler(**params)

            duration = (time.monotonic() - start) * 1000
            self._total_duration_ms += duration
            return result

        except asyncio.TimeoutError:
            self._total_errors += 1
            raise TimeoutError(
                f"Skill execution timed out after {timeout}s"
            )
        except Exception:
            self._total_errors += 1
            raise

    def get_stats(self) -> Dict[str, Any]:
        """Get execution statistics."""
        avg_duration = (
            self._total_duration_ms / self._total_executions
            if self._total_executions > 0
            else 0.0
        )
        return {
            "total_executions": self._total_executions,
            "total_errors": self._total_errors,
            "success_rate": (
                (self._total_executions - self._total_errors)
                / self._total_executions
                if self._total_executions > 0
                else 1.0
            ),
            "avg_duration_ms": round(avg_duration, 2),
        }
