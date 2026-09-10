"""
Tests for Hermes skills module.
"""

import pytest
import asyncio
from backend.hermes_engine.skills.skill_manager import SkillManager
from backend.hermes_engine.skills.skill_registry import SkillRegistry
from backend.hermes_engine.skills.skill_executor import SkillExecutor


@pytest.fixture
def skill_manager():
    return SkillManager()


@pytest.fixture
def skill_registry():
    return SkillRegistry()


@pytest.fixture
def skill_executor():
    return SkillExecutor()


class TestSkillManager:
    def test_register_and_list(self, skill_manager):
        async def handler(**kwargs):
            return "result"

        skill_manager.register("test_skill", handler, description="Test")
        skills = skill_manager.list_skills()
        assert len(skills) == 1
        assert skills[0]["name"] == "test_skill"

    @pytest.mark.asyncio
    async def test_execute(self, skill_manager):
        async def add(x, y):
            return x + y

        skill_manager.register("add", add)
        result = await skill_manager.execute("add", {"x": 2, "y": 3})
        assert result == 5

    @pytest.mark.asyncio
    async def test_execute_unknown(self, skill_manager):
        with pytest.raises(KeyError):
            await skill_manager.execute("nonexistent")


class TestSkillRegistry:
    def test_register(self, skill_registry):
        async def handler(**kwargs):
            return None

        skill_registry.register("skill1", handler, description="Test")
        assert skill_registry.has("skill1")

    def test_unregister(self, skill_registry):
        async def handler(**kwargs):
            return None

        skill_registry.register("skill1", handler)
        assert skill_registry.unregister("skill1")
        assert not skill_registry.has("skill1")


class TestSkillExecutor:
    @pytest.mark.asyncio
    async def test_execute(self, skill_executor):
        async def add(x, y):
            return x + y

        result = await skill_executor.execute(add, {"x": 5, "y": 3})
        assert result == 8

    @pytest.mark.asyncio
    async def test_execute_timeout(self, skill_executor):
        async def slow():
            await asyncio.sleep(10)
            return "done"

        with pytest.raises(TimeoutError):
            await skill_executor.execute(slow, {}, timeout=0.1)
