"""
Step 3 tests: HermesSkill.enabled enforcement on existing execution paths.

Covers both registry-backed executors without changing their contracts:
enabled skills behave exactly as before; disabled skills raise
SkillDisabledError before any counter increments or handler invocation,
checked live on every call (revocation is immediate).
"""

from __future__ import annotations

import pytest

from backend.hermes.skills.manager import SkillManager as HermesSkillManager
from backend.hermes.skills.registry import SkillDisabledError as HermesDisabledError
from backend.hermes.skills.registry import SkillRegistry as HermesRegistry
from backend.hermes_engine.skills.skill_manager import (
    SkillDisabledError as EngineDisabledError,
)
from backend.hermes_engine.skills.skill_manager import SkillManager as EngineSkillManager


async def _add(x, y):
    return x + y


@pytest.fixture
def hermes_manager():
    manager = HermesSkillManager()
    manager.register("add", _add, description="Add numbers")
    return manager


@pytest.fixture
def engine_manager():
    manager = EngineSkillManager()
    manager.register("add", _add, description="Add numbers")
    return manager


class TestHermesStackGate:
    @pytest.mark.asyncio
    async def test_enabled_by_default_executes(self, hermes_manager):
        assert await hermes_manager.execute("add", {"x": 2, "y": 3}) == 5

    @pytest.mark.asyncio
    async def test_disabled_rejected(self, hermes_manager):
        assert hermes_manager._registry.set_enabled("add", False) is True
        with pytest.raises(HermesDisabledError):
            await hermes_manager.execute("add", {"x": 2, "y": 3})

    @pytest.mark.asyncio
    async def test_disabled_counters_untouched(self, hermes_manager):
        before_stats = hermes_manager.get_stats()
        before_entry = dict(hermes_manager.get("add"))
        hermes_manager._registry.set_enabled("add", False)
        with pytest.raises(HermesDisabledError):
            await hermes_manager.execute("add", {"x": 1, "y": 1}, timeout=5)
        assert hermes_manager.get_stats() == before_stats
        entry = hermes_manager.get("add")
        assert entry["execution_count"] == before_entry["execution_count"]
        assert entry["error_count"] == before_entry["error_count"]

    @pytest.mark.asyncio
    async def test_unknown_still_key_error(self, hermes_manager):
        with pytest.raises(KeyError):
            await hermes_manager.execute("missing")

    def test_set_enabled_unknown_returns_false(self, hermes_manager):
        assert hermes_manager._registry.set_enabled("missing", False) is False
        assert hermes_manager._registry.is_enabled("missing") is False

    @pytest.mark.asyncio
    async def test_reenable_restores_execution(self, hermes_manager):
        hermes_manager._registry.set_enabled("add", False)
        with pytest.raises(HermesDisabledError):
            await hermes_manager.execute("add", {"x": 1, "y": 1})
        hermes_manager._registry.set_enabled("add", True)
        assert await hermes_manager.execute("add", {"x": 1, "y": 1}) == 2

    def test_list_exposes_flag(self, hermes_manager):
        assert hermes_manager.list_skills()[0]["enabled"] is True
        hermes_manager._registry.set_enabled("add", False)
        assert hermes_manager.list_skills()[0]["enabled"] is False


class TestEngineStackGate:
    @pytest.mark.asyncio
    async def test_enabled_by_default_executes(self, engine_manager):
        assert await engine_manager.execute("add", {"x": 2, "y": 3}) == 5

    @pytest.mark.asyncio
    async def test_disabled_rejected(self, engine_manager):
        assert engine_manager.set_enabled("add", False) is True
        with pytest.raises(EngineDisabledError):
            await engine_manager.execute("add", {"x": 2, "y": 3})

    @pytest.mark.asyncio
    async def test_disabled_counters_untouched(self, engine_manager):
        engine_manager.set_enabled("add", False)
        with pytest.raises(EngineDisabledError):
            await engine_manager.execute("add", {"x": 1, "y": 1})
        assert engine_manager._skills["add"]["execution_count"] == 0
        assert engine_manager._skills["add"]["error_count"] == 0
        assert engine_manager.get_stats()["total_executions"] == 0

    @pytest.mark.asyncio
    async def test_unknown_still_key_error(self, engine_manager):
        with pytest.raises(KeyError):
            await engine_manager.execute("missing")

    def test_set_enabled_unknown_returns_false(self, engine_manager):
        assert engine_manager.set_enabled("missing", False) is False


class TestApprovalCannotBeBypassed:
    @pytest.mark.asyncio
    async def test_revocation_takes_effect_immediately(self, hermes_manager):
        # Approved (registered) skill runs...
        assert await hermes_manager.execute("add", {"x": 1, "y": 1}) == 2
        # ...human revokes it...
        hermes_manager._registry.set_enabled("add", False)
        # ...no cached approval lets it through.
        with pytest.raises(HermesDisabledError):
            await hermes_manager.execute("add", {"x": 1, "y": 1})

    @pytest.mark.asyncio
    async def test_revocation_takes_effect_immediately_engine(self, engine_manager):
        assert await engine_manager.execute("add", {"x": 1, "y": 1}) == 2
        engine_manager.set_enabled("add", False)
        with pytest.raises(EngineDisabledError):
            await engine_manager.execute("add", {"x": 1, "y": 1})

    def test_db_flag_defaults_enabled(self):
        # The persistent HermesSkill.enabled flag this gate mirrors.
        from backend.models.hermes_skill import HermesSkill

        assert HermesSkill.__table__.c.enabled.default.arg is True
