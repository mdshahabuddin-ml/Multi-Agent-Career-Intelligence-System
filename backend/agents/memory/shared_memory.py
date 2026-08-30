from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum as PyEnum
import uuid
import asyncio
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


class MemoryScope(str, PyEnum):
    """Scope of memory visibility."""
    PRIVATE = "private"        # Only accessible by owner agent
    TEAM = "team"              # Accessible by team members
    GLOBAL = "global"          # Accessible by all agents
    CONVERSATION = "conversation"  # Tied to conversation


class MemoryType(str, PyEnum):
    """Types of memory entries."""
    FACT = "fact"
    CONTEXT = "context"
    RESULT = "result"
    DECISION = "decision"
    PREFERENCE = "preference"
    LEARNED_PATTERN = "learned_pattern"
    TEMPORARY = "temporary"
    ARTIFACT = "artifact"


@dataclass
class MemoryEntry:
    """A single memory entry."""
    memory_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str = ""
    scope: MemoryScope = MemoryScope.PRIVATE
    memory_type: MemoryType = MemoryType.FACT
    key: str = ""
    value: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: Set[str] = field(default_factory=set)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    version: int = 1
    parent_id: Optional[str] = None  # For versioning
    
    def is_expired(self) -> bool:
        if self.expires_at:
            return datetime.utcnow() > self.expires_at
        return False
    
    def access(self) -> None:
        self.access_count += 1
        self.last_accessed = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "memory_id": self.memory_id,
            "agent_id": self.agent_id,
            "scope": self.scope.value,
            "memory_type": self.memory_type.value,
            "key": self.key,
            "value": self.value,
            "metadata": self.metadata,
            "tags": list(self.tags),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed.isoformat() if self.last_accessed else None,
            "version": self.version,
            "parent_id": self.parent_id,
        }


@dataclass
class ConversationContext:
    """Context for a conversation/shared session."""
    conversation_id: str
    participants: Set[str] = field(default_factory=set)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    active_agents: Set[str] = field(default_factory=set)
    shared_artifacts: Dict[str, Any] = field(default_factory=dict)
    decisions: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "conversation_id": self.conversation_id,
            "participants": list(self.participants),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
            "active_agents": list(self.active_agents),
            "shared_artifacts": self.shared_artifacts,
            "decisions": self.decisions,
        }


class SharedMemory:
    """Shared memory system for multi-agent collaboration."""
    
    def __init__(self):
        self._memories: Dict[str, MemoryEntry] = {}  # memory_id -> MemoryEntry
        self._agent_index: Dict[str, Set[str]] = defaultdict(set)  # agent_id -> set of memory_ids
        self._scope_index: Dict[MemoryScope, Set[str]] = defaultdict(set)  # scope -> set of memory_ids
        self._key_index: Dict[str, Dict[str, str]] = defaultdict(dict)  # agent_id -> key -> memory_id
        self._conversations: Dict[str, ConversationContext] = {}
        self._team_memberships: Dict[str, Set[str]] = defaultdict(set)  # team_id -> agent_ids
        self._agent_teams: Dict[str, Set[str]] = defaultdict(set)  # agent_id -> team_ids
        self._locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._cleanup_task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start background cleanup task."""
        self._cleanup_task = asyncio.create_task(self._cleanup_expired())
    
    async def stop(self):
        """Stop background cleanup task."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
    
    async def _cleanup_expired(self):
        """Periodically clean up expired memories."""
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour
                now = datetime.utcnow()
                expired = [
                    mid for mid, mem in self._memories.items()
                    if mem.is_expired()
                ]
                for mid in expired:
                    await self.delete(mid)
                if expired:
                    logger.info(f"Cleaned up {len(expired)} expired memories")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Memory cleanup error: {e}")
    
    async def store(
        self,
        agent_id: str,
        key: str,
        value: Any,
        scope: MemoryScope = MemoryScope.PRIVATE,
        memory_type: MemoryType = MemoryType.FACT,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[Set[str]] = None,
        expires_in: Optional[timedelta] = None,
        team_id: Optional[str] = None,
    ) -> MemoryEntry:
        """Store a memory entry."""
        async with self._locks[f"store_{agent_id}_{key}"]:
            # Check if key exists for agent
            existing_id = self._key_index[agent_id].get(key)
            
            if existing_id and existing_id in self._memories:
                # Update existing
                entry = self._memories[existing_id]
                entry.value = value
                entry.metadata.update(metadata or {})
                if tags:
                    entry.tags.update(tags)
                entry.updated_at = datetime.utcnow()
                entry.version += 1
                if expires_in:
                    entry.expires_at = datetime.utcnow() + expires_in
            else:
                # Create new
                entry = MemoryEntry(
                    agent_id=agent_id,
                    scope=scope,
                    memory_type=memory_type,
                    key=key,
                    value=value,
                    metadata=metadata or {},
                    tags=tags or set(),
                )
                if expires_in:
                    entry.expires_at = datetime.utcnow() + expires_in
                
                # Handle team scope
                if scope == MemoryScope.TEAM and team_id:
                    entry.metadata["team_id"] = team_id
                
                self._memories[entry.memory_id] = entry
                self._agent_index[agent_id].add(entry.memory_id)
                self._scope_index[scope].add(entry.memory_id)
                self._key_index[agent_id][key] = entry.memory_id
            
            return entry
    
    async def get(
        self,
        agent_id: str,
        key: str,
        include_team: bool = True,
    ) -> Optional[MemoryEntry]:
        """Get a memory entry by key."""
        # Try private first
        memory_id = self._key_index[agent_id].get(key)
        if memory_id and memory_id in self._memories:
            entry = self._memories[memory_id]
            if not entry.is_expired():
                entry.access()
                return entry
        
        # Try team memories if allowed
        if include_team:
            for team_id in self._agent_teams[agent_id]:
                team_key = f"{team_id}:{key}"
                memory_id = self._key_index.get(f"team_{team_id}", {}).get(team_key)
                if memory_id and memory_id in self._memories:
                    entry = self._memories[memory_id]
                    if not entry.is_expired():
                        entry.access()
                        return entry
        
        # Try global
        global_key = f"global:{key}"
        memory_id = self._key_index.get("global", {}).get(global_key)
        if memory_id and memory_id in self._memories:
            entry = self._memories[memory_id]
            if not entry.is_expired():
                entry.access()
                return entry
        
        return None
    
    async def search(
        self,
        agent_id: str,
        query: str = "",
        memory_type: Optional[MemoryType] = None,
        tags: Optional[Set[str]] = None,
        scope: Optional[MemoryScope] = None,
        limit: int = 50,
    ) -> List[MemoryEntry]:
        """Search memories."""
        candidate_ids = set()
        
        # Determine candidate memories based on scope access
        accessible_scopes = [MemoryScope.PRIVATE]
        if scope:
            accessible_scopes = [scope]
        else:
            accessible_scopes.extend([MemoryScope.GLOBAL, MemoryScope.CONVERSATION])
            for team_id in self._agent_teams[agent_id]:
                accessible_scopes.append(MemoryScope.TEAM)
        
        for s in accessible_scopes:
            candidate_ids.update(self._scope_index.get(s, set()))
        
        # Filter by agent ownership for private
        private_ids = self._agent_index.get(agent_id, set())
        candidate_ids.update(private_ids)
        
        results = []
        for mid in candidate_ids:
            if mid not in self._memories:
                continue
            entry = self._memories[mid]
            
            if entry.is_expired():
                continue
            
            if memory_type and entry.memory_type != memory_type:
                continue
            
            if tags and not tags.issubset(entry.tags):
                continue
            
            if query:
                query_lower = query.lower()
                if (query_lower not in str(entry.value).lower() and
                    query_lower not in entry.key.lower() and
                    not any(query_lower in tag.lower() for tag in entry.tags)):
                    continue
            
            results.append(entry)
            if len(results) >= limit:
                break
        
        # Sort by relevance (access count, recency)
        results.sort(key=lambda e: (e.access_count, e.updated_at), reverse=True)
        return results
    
    async def delete(self, memory_id: str, agent_id: str) -> bool:
        """Delete a memory entry."""
        if memory_id not in self._memories:
            return False
        
        entry = self._memories[memory_id]
        
        # Check permissions
        if entry.agent_id != agent_id and entry.scope != MemoryScope.GLOBAL:
            # Check if agent is in same team for team memories
            if entry.scope == MemoryScope.TEAM:
                team_id = entry.metadata.get("team_id")
                if team_id and team_id not in self._agent_teams[agent_id]:
                    return False
            else:
                return False
        
        # Remove from indices
        self._memories.pop(memory_id, None)
        self._agent_index[entry.agent_id].discard(memory_id)
        self._scope_index[entry.scope].discard(memory_id)
        self._key_index[entry.agent_id].pop(entry.key, None)
        
        return True
    
    async def create_conversation(
        self,
        conversation_id: str,
        participants: Set[str],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ConversationContext:
        """Create a new conversation context."""
        context = ConversationContext(
            conversation_id=conversation_id,
            participants=participants,
            metadata=metadata or {},
        )
        self._conversations[conversation_id] = context
        return context
    
    async def get_conversation(self, conversation_id: str) -> Optional[ConversationContext]:
        """Get conversation context."""
        return self._conversations.get(conversation_id)
    
    async def update_conversation(
        self,
        conversation_id: str,
        updates: Dict[str, Any],
        agent_id: str,
    ) -> Optional[ConversationContext]:
        """Update conversation context."""
        context = self._conversations.get(conversation_id)
        if not context:
            return None
        
        if agent_id not in context.participants:
            return None
        
        context.metadata.update(updates.get("metadata", {}))
        if "shared_artifacts" in updates:
            context.shared_artifacts.update(updates["shared_artifacts"])
        if "decisions" in updates:
            context.decisions.extend(updates["decisions"])
        
        context.active_agents.add(agent_id)
        context.updated_at = datetime.utcnow()
        
        return context
    
    async def add_team_member(self, team_id: str, agent_id: str) -> None:
        """Add agent to team."""
        self._team_memberships[team_id].add(agent_id)
        self._agent_teams[agent_id].add(team_id)
    
    async def remove_team_member(self, team_id: str, agent_id: str) -> None:
        """Remove agent from team."""
        self._team_memberships[team_id].discard(agent_id)
        self._agent_teams[agent_id].discard(team_id)
    
    async def get_team_memories(self, team_id: str, agent_id: str) -> List[MemoryEntry]:
        """Get all memories for a team (if agent is member)."""
        if team_id not in self._agent_teams[agent_id]:
            return []
        
        results = []
        for mid in self._scope_index.get(MemoryScope.TEAM, set()):
            if mid in self._memories:
                entry = self._memories[mid]
                if entry.metadata.get("team_id") == team_id and not entry.is_expired():
                    results.append(entry)
        
        return results
    
    async def get_stats(self, agent_id: str) -> Dict[str, Any]:
        """Get memory statistics for agent."""
        private_count = len(self._agent_index.get(agent_id, set()))
        
        team_count = 0
        for team_id in self._agent_teams[agent_id]:
            team_count += len(await self.get_team_memories(team_id, agent_id))
        
        global_count = len(self._scope_index.get(MemoryScope.GLOBAL, set()))
        
        return {
            "private_memories": private_count,
            "team_memories": team_count,
            "global_memories": global_count,
            "teams": list(self._agent_teams[agent_id]),
            "conversations": len([c for c in self._conversations.values() if agent_id in c.participants]),
        }


# Global shared memory instance
shared_memory = SharedMemory()


# Convenience functions
async def remember(
    agent_id: str,
    key: str,
    value: Any,
    scope: MemoryScope = MemoryScope.PRIVATE,
    **kwargs
) -> MemoryEntry:
    """Store a memory."""
    return await shared_memory.store(agent_id, key, value, scope, **kwargs)


async def recall(
    agent_id: str,
    key: str,
    **kwargs
) -> Optional[MemoryEntry]:
    """Recall a memory."""
    return await shared_memory.get(agent_id, key, **kwargs)


async def search_memory(
    agent_id: str,
    query: str = "",
    **kwargs
) -> List[MemoryEntry]:
    """Search memories."""
    return await shared_memory.search(agent_id, query, **kwargs)


async def start_conversation(
    conversation_id: str,
    participants: Set[str],
    **kwargs
) -> ConversationContext:
    """Start a conversation."""
    return await shared_memory.create_conversation(conversation_id, participants, **kwargs)


async def get_conversation(conversation_id: str) -> Optional[ConversationContext]:
    """Get conversation context."""
    return await shared_memory.get_conversation(conversation_id)