"""
Tests for Hermes delegation module.
"""

import pytest
import asyncio
from backend.hermes_engine.delegation.subagent_manager import SubAgentManager
from backend.hermes_engine.delegation.parallel_executor import ParallelExecutor
from backend.hermes_engine.delegation.task_router import TaskRouter
from backend.hermes_engine.core.hermes_agent import HermesAgent, HermesAgentConfig


@pytest.fixture
def subagent_manager():
    return SubAgentManager()


@pytest.fixture
def parallel_executor():
    return ParallelExecutor(max_concurrent=3)


@pytest.fixture
def task_router():
    return TaskRouter()


class TestSubAgentManager:
    def test_register(self, subagent_manager):
        agent = HermesAgent(HermesAgentConfig(name="test"))
        subagent_manager.register(agent)
        agents = subagent_manager.get_all()
        assert len(agents) == 1

    def test_unregister(self, subagent_manager):
        agent = HermesAgent(HermesAgentConfig(name="test"))
        subagent_manager.register(agent)
        assert subagent_manager.unregister(agent.agent_id)
        assert len(subagent_manager.get_all()) == 0


class TestParallelExecutor:
    @pytest.mark.asyncio
    async def test_execute(self, parallel_executor):
        async def handler(task):
            return {"result": task.get("value")}

        tasks = [{"id": "1", "value": "a"}, {"id": "2", "value": "b"}]
        results = await parallel_executor.execute(tasks, handler)
        assert len(results) == 2
        assert all(r["success"] for r in results)


class TestTaskRouter:
    def test_register_handler(self, task_router):
        async def handler(task):
            return "handled"

        task_router.register("test", handler)
        assert "test" in task_router.list_types()

    @pytest.mark.asyncio
    async def test_route(self, task_router):
        async def handler(task):
            return "handled"

        task_router.register("test", handler)
        result = await task_router.route({"type": "test"})
        assert result == "handled"
