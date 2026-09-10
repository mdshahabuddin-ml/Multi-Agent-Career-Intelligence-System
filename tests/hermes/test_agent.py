"""
Tests for Hermes core modules (Agent, State, Task).
"""

import pytest
import asyncio
from backend.hermes.core.agent import Agent, AgentConfig
from backend.hermes.core.state import AgentState, StateManager
from backend.hermes.core.task import Task, TaskResult, TaskStatus


class SimpleAgent(Agent):
    """A simple agent for testing purposes."""

    async def _process_task(self, task):
        return TaskResult(
            task_id=task.id,
            success=True,
            output={"processed": True},
        )


class FailingAgent(Agent):
    """An agent that always fails for testing."""

    async def _process_task(self, task):
        raise ValueError("Intentional failure")


class TestAgent:
    def test_agent_creation(self):
        config = AgentConfig(name="test_agent", description="Test agent")
        agent = SimpleAgent(config)
        assert agent.name == "test_agent"
        assert not agent.is_busy

    def test_agent_state(self):
        config = AgentConfig(name="test_agent")
        agent = SimpleAgent(config)
        state = agent.get_state()
        assert state["name"] == "test_agent"
        assert state["id"] == agent.id
        assert state["tasks_completed"] == 0

    @pytest.mark.asyncio
    async def test_agent_execute(self):
        config = AgentConfig(name="test_agent")
        agent = SimpleAgent(config)
        task = Task(description="Test task")
        result = await agent.execute(task)
        assert result.success
        assert result.output["processed"] is True
        assert len(agent.get_history()) == 1

    @pytest.mark.asyncio
    async def test_agent_execute_failure(self):
        config = AgentConfig(name="failing_agent")
        agent = FailingAgent(config)
        task = Task(description="Test task")
        result = await agent.execute(task)
        assert not result.success
        assert "Intentional failure" in result.error


class TestTask:
    def test_task_creation(self):
        task = Task(description="Test task", type="test")
        assert task.description == "Test task"
        assert task.type == "test"
        assert task.status == TaskStatus.PENDING

    def test_task_lifecycle(self):
        task = Task(description="Test task")
        task.start()
        assert task.status == TaskStatus.IN_PROGRESS
        assert task.started_at is not None

        task.complete()
        assert task.status == TaskStatus.COMPLETED
        assert task.completed_at is not None
        assert task.is_terminal

    def test_task_failure(self):
        task = Task(description="Test task")
        task.fail("Something went wrong")
        assert task.status == TaskStatus.FAILED
        assert task.metadata["error"] == "Something went wrong"
        assert task.is_terminal

    def test_task_cancel(self):
        task = Task(description="Test task")
        task.cancel()
        assert task.status == TaskStatus.CANCELLED
        assert task.is_terminal

    def test_task_to_dict(self):
        task = Task(description="Test task", type="test")
        d = task.to_dict()
        assert d["description"] == "Test task"
        assert d["type"] == "test"
        assert "id" in d


class TestStateManager:
    def test_register_agent(self):
        manager = StateManager()
        state = manager.register("agent_1")
        assert state.agent_id == "agent_1"
        assert "agent_1" in [s.agent_id for s in manager.get_all().values()]

    def test_get_agent_state(self):
        manager = StateManager()
        manager.register("agent_1")
        state = manager.get("agent_1")
        assert state is not None
        assert state.agent_id == "agent_1"

    def test_remove_agent(self):
        manager = StateManager()
        manager.register("agent_1")
        assert manager.remove("agent_1")
        assert manager.get("agent_1") is None

    def test_clear_all(self):
        manager = StateManager()
        manager.register("agent_1")
        manager.register("agent_2")
        manager.clear()
        assert len(manager.get_all()) == 0
