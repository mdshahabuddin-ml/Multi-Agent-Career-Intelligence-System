"""
Content Worker - Background content processing.
"""

from __future__ import annotations

import logging
import asyncio
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class ContentWorker:
    """
    Background worker for content processing.
    """

    def __init__(self):
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start the worker."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("ContentWorker started")

    async def stop(self) -> None:
        """Stop the worker."""
        self._running = False
        if self._task:
            self._task.cancel()
        logger.info("ContentWorker stopped")

    async def _run_loop(self) -> None:
        """Main worker loop."""
        while self._running:
            try:
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                break
