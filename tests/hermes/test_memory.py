"""
Tests for Hermes memory module.
"""

import pytest
import asyncio
from backend.hermes_engine.memory.memory_manager import MemoryManager
from backend.hermes_engine.memory.conversation_memory import ConversationMemory
from backend.hermes_engine.memory.user_memory import UserMemory


@pytest.fixture
def memory_manager():
    return MemoryManager()


@pytest.fixture
def conversation_memory():
    return ConversationMemory()


@pytest.fixture
def user_memory():
    return UserMemory()


class TestMemoryManager:
    @pytest.mark.asyncio
    async def test_store_and_retrieve(self, memory_manager):
        memory_id = await memory_manager.store(
            agent_id="agent-1",
            content="Test memory",
            category="test",
        )
        assert memory_id is not None

        memories = await memory_manager.retrieve(agent_id="agent-1")
        assert len(memories) == 1

    @pytest.mark.asyncio
    async def test_delete_memory(self, memory_manager):
        memory_id = await memory_manager.store(agent_id="agent-1", content="To delete")
        deleted = await memory_manager.delete(memory_id=memory_id, agent_id="agent-1")
        assert deleted

    @pytest.mark.asyncio
    async def test_clear_agent(self, memory_manager):
        await memory_manager.store(agent_id="agent-1", content="Memory 1")
        await memory_manager.store(agent_id="agent-1", content="Memory 2")
        count = await memory_manager.clear_agent(agent_id="agent-1")
        assert count == 2


class TestConversationMemory:
    def test_add_and_get(self, conversation_memory):
        conversation_memory.add_message("conv1", "user", "Hello")
        history = conversation_memory.get_history("conv1")
        assert len(history) == 1
        assert history[0]["content"] == "Hello"

    def test_clear(self, conversation_memory):
        conversation_memory.add_message("conv1", "user", "Hello")
        conversation_memory.clear("conv1")
        assert len(conversation_memory.get_history("conv1")) == 0


class TestUserMemory:
    def test_store_and_retrieve(self, user_memory):
        user_memory.store("user1", "theme", "dark")
        value = user_memory.retrieve("user1", "theme")
        assert value == "dark"

    def test_delete(self, user_memory):
        user_memory.store("user1", "theme", "dark")
        deleted = user_memory.delete("user1", "theme")
        assert deleted
        assert user_memory.retrieve("user1", "theme") is None
