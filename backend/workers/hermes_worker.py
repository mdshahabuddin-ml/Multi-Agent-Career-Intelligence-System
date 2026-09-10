"""
Hermes Worker - Background task processing for Hermes.
"""

from __future__ import annotations

import logging
import asyncio
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class HermesWorker:
    """
    Background worker for Hermes agent tasks.
    """

    def __init__(self):
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._queue: asyncio.Queue = asyncio.Queue()

    async def start(self) -> None:
        """Start the worker."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("HermesWorker started")

    async def stop(self) -> None:
        """Stop the worker."""
        self._running = False
        if self._task:
            self._task.cancel()
        logger.info("HermesWorker stopped")

    async def submit(self, task: Dict[str, Any]) -> None:
        """Submit a task to the worker."""
        await self._queue.put(task)

    async def _run_loop(self) -> None:
        """Main worker loop."""
        while self._running:
            try:
                task = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                await self._process_task(task)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Worker error: {e}")

    async def _process_task(self, task: Dict[str, Any]) -> None:
        """Process a task."""
        logger.info(f"Processing task: {task.get('type', 'unknown')}")
