from typing import List, Dict, Any, Optional, Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum as PyEnum
import uuid
import asyncio
import logging

logger = logging.getLogger(__name__)


class MessageType(str, PyEnum):
    """Types of messages in agent communication."""
    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    BROADCAST = "broadcast"
    QUERY = "query"
    RESULT = "result"
    ERROR = "error"
    HEARTBEAT = "heartbeat"
    HANDOFF = "handoff"
    DELEGATE = "delegate"
    COLLABORATE = "collaborate"
    CONSENSUS_REQUEST = "consensus_request"
    CONSENSUS_VOTE = "consensus_vote"
    DEBATE_ARGUMENT = "debate_argument"
    DEBATE_COUNTER = "debate_counter"
    HUMAN_INPUT_REQUEST = "human_input_request"
    HUMAN_INPUT_RESPONSE = "human_input_response"


class MessagePriority(str, PyEnum):
    """Message priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AgentMessage:
    """Standard message format for agent communication."""
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    message_type: MessageType = MessageType.REQUEST
    sender_id: str = ""
    recipient_id: Optional[str] = None  # None for broadcast
    conversation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    payload: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    priority: MessagePriority = MessagePriority.NORMAL
    timestamp: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    requires_response: bool = False
    response_to: Optional[str] = None  # message_id this responds to
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "message_id": self.message_id,
            "message_type": self.message_type.value,
            "sender_id": self.sender_id,
            "recipient_id": self.recipient_id,
            "conversation_id": self.conversation_id,
            "payload": self.payload,
            "metadata": self.metadata,
            "priority": self.priority.value,
            "timestamp": self.timestamp.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "requires_response": self.requires_response,
            "response_to": self.response_to,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentMessage":
        return cls(
            message_id=data["message_id"],
            message_type=MessageType(data["message_type"]),
            sender_id=data["sender_id"],
            recipient_id=data.get("recipient_id"),
            conversation_id=data["conversation_id"],
            payload=data["payload"],
            metadata=data.get("metadata", {}),
            priority=MessagePriority(data.get("priority", "normal")),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None,
            requires_response=data.get("requires_response", False),
            response_to=data.get("response_to"),
        )


class CommunicationChannel:
    """Abstract communication channel between agents."""
    
    def __init__(self, channel_id: str):
        self.channel_id = channel_id
        self._subscribers: Dict[str, List[Callable[[AgentMessage], Awaitable[None]]]] = {}
        self._message_history: List[AgentMessage] = []
        self._max_history = 1000
    
    async def publish(self, message: AgentMessage) -> None:
        """Publish message to channel."""
        self._message_history.append(message)
        if len(self._message_history) > self._max_history:
            self._message_history = self._message_history[-self._max_history:]
        
        # Notify subscribers
        handlers = self._subscribers.get(message.message_type, [])
        for handler in handlers:
            try:
                await handler(message)
            except Exception as e:
                logger.error(f"Handler error for {message.message_type}: {e}")
    
    def subscribe(self, message_type: MessageType, handler: Callable[[AgentMessage], Awaitable[None]]) -> None:
        """Subscribe to message type."""
        if message_type not in self._subscribers:
            self._subscribers[message_type] = []
        self._subscribers[message_type].append(handler)
    
    def unsubscribe(self, message_type: MessageType, handler: Callable) -> None:
        """Unsubscribe from message type."""
        if message_type in self._subscribers:
            self._subscribers[message_type] = [h for h in self._subscribers[message_type] if h != handler]
    
    def get_history(self, message_type: Optional[MessageType] = None, limit: int = 100) -> List[AgentMessage]:
        """Get message history."""
        messages = self._message_history
        if message_type:
            messages = [m for m in messages if m.message_type == message_type]
        return messages[-limit:]


class MessageBus:
    """Central message bus for agent communication."""
    
    def __init__(self):
        self._channels: Dict[str, CommunicationChannel] = {}
        self._agent_channels: Dict[str, str] = {}  # agent_id -> channel_id
        self._global_channel = CommunicationChannel("global")
        self._channels["global"] = self._global_channel
    
    def register_agent(self, agent_id: str, channel_id: str = "global") -> None:
        """Register agent to a channel."""
        self._agent_channels[agent_id] = channel_id
        if channel_id not in self._channels:
            self._channels[channel_id] = CommunicationChannel(channel_id)
    
    def unregister_agent(self, agent_id: str) -> None:
        """Unregister agent."""
        self._agent_channels.pop(agent_id, None)
    
    async def send(self, message: AgentMessage) -> None:
        """Send message to recipient or broadcast."""
        if message.recipient_id:
            # Direct message
            channel_id = self._agent_channels.get(message.recipient_id, "global")
            channel = self._channels.get(channel_id)
            if channel:
                await channel.publish(message)
        else:
            # Broadcast to all in sender's channel
            sender_channel = self._agent_channels.get(message.sender_id, "global")
            channel = self._channels.get(sender_channel)
            if channel:
                await channel.publish(message)
    
    async def broadcast(self, message: AgentMessage, channel_id: str = "global") -> None:
        """Broadcast message to channel."""
        channel = self._channels.get(channel_id)
        if channel:
            await channel.publish(message)
    
    def subscribe(self, agent_id: str, message_type: MessageType, handler: Callable[[AgentMessage], Awaitable[None]]) -> None:
        """Subscribe agent to message type."""
        channel_id = self._agent_channels.get(agent_id, "global")
        channel = self._channels.get(channel_id)
        if channel:
            channel.subscribe(message_type, handler)
    
    def get_channel(self, channel_id: str) -> Optional[CommunicationChannel]:
        """Get channel by ID."""
        return self._channels.get(channel_id)
    
    def create_channel(self, channel_id: str) -> CommunicationChannel:
        """Create new channel."""
        channel = CommunicationChannel(channel_id)
        self._channels[channel_id] = channel
        return channel


# Global message bus instance
message_bus = MessageBus()


def create_request(
    sender_id: str,
    recipient_id: str,
    action: str,
    payload: Dict[str, Any],
    conversation_id: Optional[str] = None,
    requires_response: bool = True,
) -> AgentMessage:
    """Create a request message."""
    return AgentMessage(
        message_type=MessageType.REQUEST,
        sender_id=sender_id,
        recipient_id=recipient_id,
        conversation_id=conversation_id or str(uuid.uuid4()),
        payload={"action": action, **payload},
        requires_response=requires_response,
    )


def create_response(
    sender_id: str,
    original_message: AgentMessage,
    payload: Dict[str, Any],
    success: bool = True,
) -> AgentMessage:
    """Create a response message."""
    return AgentMessage(
        message_type=MessageType.RESPONSE,
        sender_id=sender_id,
        recipient_id=original_message.sender_id,
        conversation_id=original_message.conversation_id,
        payload={"success": success, **payload},
        response_to=original_message.message_id,
    )


def create_notification(
    sender_id: str,
    event: str,
    payload: Dict[str, Any],
    recipient_id: Optional[str] = None,
) -> AgentMessage:
    """Create a notification message."""
    return AgentMessage(
        message_type=MessageType.NOTIFICATION,
        sender_id=sender_id,
        recipient_id=recipient_id,
        payload={"event": event, **payload},
    )


def create_handoff(
    sender_id: str,
    recipient_id: str,
    task: str,
    context: Dict[str, Any],
    conversation_id: Optional[str] = None,
) -> AgentMessage:
    """Create a handoff message to delegate task."""
    return AgentMessage(
        message_type=MessageType.HANDOFF,
        sender_id=sender_id,
        recipient_id=recipient_id,
        conversation_id=conversation_id or str(uuid.uuid4()),
        payload={"task": task, "context": context},
        requires_response=True,
    )