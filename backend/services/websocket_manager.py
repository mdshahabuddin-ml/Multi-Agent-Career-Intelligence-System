import logging
from typing import Dict, Optional
from fastapi import WebSocket
import asyncio
import os

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Manages WebSocket connections for real-time progress updates (local mode)."""

    def __init__(self):
        self.active_connections: Dict[int, WebSocket] = {}
        self._lock = asyncio.Lock()

    async def connect(self, research_id: int, websocket: WebSocket):
        """Register a new WebSocket connection."""
        await websocket.accept()
        async with self._lock:
            self.active_connections[research_id] = websocket
        logger.info(f"WebSocket connected for research {research_id}")

    async def disconnect(self, research_id: int):
        """Remove a WebSocket connection."""
        async with self._lock:
            self.active_connections.pop(research_id, None)
        logger.info(f"WebSocket disconnected for research {research_id}")

    async def send_progress(self, research_id: int, data: dict):
        """Send progress update to connected client."""
        async with self._lock:
            websocket = self.active_connections.get(research_id)
        
        if websocket:
            try:
                await websocket.send_json(data)
            except Exception as e:
                logger.warning(f"Failed to send progress for research {research_id}: {e}")
                await self.disconnect(research_id)

    async def broadcast(self, data: dict):
        """Broadcast to all connected clients."""
        async with self._lock:
            connections = list(self.active_connections.items())
        
        for research_id, websocket in connections:
            try:
                await websocket.send_json(data)
            except Exception as e:
                logger.warning(f"Failed to broadcast to research {research_id}: {e}")


class WebSocketManagerInterface:
    """Interface for WebSocket managers."""
    
    async def connect(self, research_id: int, websocket: WebSocket):
        raise NotImplementedError
    
    async def disconnect(self, research_id: int):
        raise NotImplementedError
    
    async def send_progress(self, research_id: int, data: dict):
        raise NotImplementedError


# Global WebSocket manager instances
_ws_manager: Optional[WebSocketManager] = None
_redis_ws_manager: Optional["RedisWebSocketManager"] = None
_use_redis = os.getenv("WEBSOCKET_USE_REDIS", "false").lower() == "true"


async def get_ws_manager() -> WebSocketManagerInterface:
    """Get the appropriate WebSocket manager based on configuration."""
    global _ws_manager, _redis_ws_manager
    
    if _use_redis:
        if _redis_ws_manager is None:
            from backend.services.redis_websocket_manager import RedisWebSocketManager, get_redis_ws_manager as get_redis
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            _redis_ws_manager = await get_redis(redis_url)
        return _redis_ws_manager
    else:
        if _ws_manager is None:
            _ws_manager = WebSocketManager()
        return _ws_manager


async def close_ws_manager():
    """Close the WebSocket manager."""
    global _ws_manager, _redis_ws_manager
    if _redis_ws_manager:
        from backend.services.redis_websocket_manager import close_redis_ws_manager
        await close_redis_ws_manager()
        _redis_ws_manager = None
    _ws_manager = None


async def notify_research_progress(research_id: int, update: dict):
    """Convenience function to send progress update."""
    manager = await get_ws_manager()
    await manager.send_progress(research_id, update)