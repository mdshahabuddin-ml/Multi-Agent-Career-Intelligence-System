import logging
import json
import asyncio
from typing import Dict, Optional, Set
from fastapi import WebSocket
import redis.asyncio as redis

logger = logging.getLogger(__name__)


class RedisWebSocketManager:
    """Redis-backed WebSocket manager for horizontal scaling."""
    
    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.redis_url = redis_url
        self.redis: Optional[redis.Redis] = None
        self.pubsub: Optional[redis.client.PubSub] = None
        self.local_connections: Dict[int, WebSocket] = {}
        self._lock = asyncio.Lock()
        self._listener_task: Optional[asyncio.Task] = None
        self._running = False
        
    async def initialize(self):
        """Initialize Redis connection and start listener."""
        if self._running:
            return
            
        self.redis = redis.from_url(self.redis_url, decode_responses=True)
        self.pubsub = self.redis.pubsub()
        await self.pubsub.subscribe("research_progress")
        self._running = True
        self._listener_task = asyncio.create_task(self._listen_for_messages())
        logger.info("RedisWebSocketManager initialized")

    async def close(self):
        """Close Redis connection and stop listener."""
        self._running = False
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
        if self.pubsub:
            await self.pubsub.unsubscribe("research_progress")
            await self.pubsub.close()
        if self.redis:
            await self.redis.close()
        logger.info("RedisWebSocketManager closed")

    async def _listen_for_messages(self):
        """Listen for messages from Redis pub/sub."""
        try:
            async for message in self.pubsub.listen():
                if message["type"] == "message":
                    await self._handle_message(message["data"])
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Redis listener error: {e}")

    async def _handle_message(self, data: str):
        """Handle incoming message from Redis."""
        try:
            payload = json.loads(data)
            research_id = payload.get("research_id")
            if research_id in self.local_connections:
                websocket = self.local_connections[research_id]
                try:
                    await websocket.send_json(payload)
                except Exception as e:
                    logger.warning(f"Failed to send to local connection {research_id}: {e}")
        except Exception as e:
            logger.error(f"Error handling Redis message: {e}")

    async def connect(self, research_id: int, websocket: WebSocket):
        """Register a new WebSocket connection."""
        await websocket.accept()
        async with self._lock:
            self.local_connections[research_id] = websocket
        logger.info(f"WebSocket connected for research {research_id}")

    async def disconnect(self, research_id: int):
        """Remove a WebSocket connection."""
        async with self._lock:
            self.local_connections.pop(research_id, None)
        logger.info(f"WebSocket disconnected for research {research_id}")

    async def send_progress(self, research_id: int, data: dict):
        """Send progress update - publishes to Redis for all workers."""
        # Publish to Redis for other workers
        if self.redis:
            try:
                await self.redis.publish("research_progress", json.dumps(data))
            except Exception as e:
                logger.error(f"Failed to publish to Redis: {e}")
        
        # Send to local connection if exists
        async with self._lock:
            websocket = self.local_connections.get(research_id)
        
        if websocket:
            try:
                await websocket.send_json(data)
            except Exception as e:
                logger.warning(f"Failed to send progress for research {research_id}: {e}")
                await self.disconnect(research_id)


# Global Redis WebSocket manager instance
_redis_ws_manager: Optional[RedisWebSocketManager] = None


async def get_redis_ws_manager(redis_url: str = "redis://localhost:6379/0") -> RedisWebSocketManager:
    """Get or create the global Redis WebSocket manager."""
    global _redis_ws_manager
    if _redis_ws_manager is None:
        _redis_ws_manager = RedisWebSocketManager(redis_url)
        await _redis_ws_manager.initialize()
    return _redis_ws_manager


async def close_redis_ws_manager():
    """Close the global Redis WebSocket manager."""
    global _redis_ws_manager
    if _redis_ws_manager:
        await _redis_ws_manager.close()
        _redis_ws_manager = None


async def notify_research_progress_redis(research_id: int, update: dict):
    """Convenience function to send progress update via Redis."""
    manager = await get_redis_ws_manager()
    await manager.send_progress(research_id, update)