"""
Tests for Hermes automation module.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from backend.hermes_engine.automation.automation_manager import AutomationManager
from backend.hermes_engine.automation.scheduler import Scheduler
from backend.hermes_engine.automation.task_runner import TaskRunner
from backend.hermes_engine.automation.trigger_manager import TriggerManager


@pytest.fixture
def automation_manager():
    return AutomationManager()


@pytest.fixture
def scheduler():
    return Scheduler()


@pytest.fixture
def task_runner():
    return TaskRunner(max_concurrent=3)


@pytest.fixture
def trigger_manager():
    return TriggerManager()


class TestAutomationManager:
    def test_create(self, automation_manager):
        async def handler():
            return "done"

        automation_id = automation_manager.create("test", handler)
        assert automation_id is not None

    @pytest.mark.asyncio
    async def test_execute(self, automation_manager):
        async def handler():
            return "done"

        automation_id = automation_manager.create("test", handler)
        result = await automation_manager.execute(automation_id)
        assert result == "done"


class TestScheduler:
    def test_schedule(self, scheduler):
        async def handler():
            pass

        task = scheduler.schedule(
            task_id="task1",
            handler=handler,
            run_at=datetime.utcnow() + timedelta(hours=1),
        )
        assert task.task_id == "task1"

    def test_cancel(self, scheduler):
        async def handler():
            pass

        scheduler.schedule(
            task_id="task1",
            handler=handler,
            run_at=datetime.utcnow() + timedelta(hours=1),
        )
        assert scheduler.cancel("task1")


class TestTaskRunner:
    @pytest.mark.asyncio
    async def test_submit(self, task_runner):
        async def handler(task):
            return {"result": "done"}

        task_runner.register_handler("test", handler)
        result = await task_runner.submit({"type": "test", "id": "1"})
        assert result["success"]


class TestTriggerManager:
    def test_register(self, trigger_manager):
        async def handler(**kwargs):
            return "triggered"

        trigger_manager.register("test_trigger", "test_event", handler)
        triggers = trigger_manager.list_triggers()
        assert len(triggers) == 1

    @pytest.mark.asyncio
    async def test_fire(self, trigger_manager):
        async def handler(**kwargs):
            return "triggered"

        trigger_manager.register("test_trigger", "test_event", handler)
        results = await trigger_manager.fire("test_event")
        assert len(results) == 1
