"""
Tests for the Hermes Agent core: lifecycle, task representation,
agent execution, planning and delegation interfaces.
"""

import asyncio

import pytest

from backend.hermes_engine.core.hermes_agent import HermesAgent, HermesAgentConfig, AgentState
from backend.hermes_engine.core.hermes_state import TaskState
from backend.hermes_engine.core.lifecycle import (
    TransitionError,
    cancel,
    run_with_lifecycle,
    transition,
)
from backend.hermes_engine.core.result import HermesResult
from backend.hermes_engine.core.task import HermesTask, TaskPriority, TaskType
from backend.hermes_engine.delegation.subagent_manager import SubAgentManager
from backend.hermes_engine.planning.planner import TaskPlanner
from backend.hermes_engine.supervisor.agent_router import AgentRouter
from backend.hermes_engine.supervisor.hermes_supervisor import HermesSupervisor


class EchoAgent(HermesAgent):
    """Sub-agent that echoes input (no LLM needed)."""

    async def _process_task(self, task, input_data, context):
        await asyncio.sleep(0)
        return {"echo": input_data}


class BoomAgent(HermesAgent):
    """Sub-agent that always fails."""

    async def _process_task(self, task, input_data, context):
        raise RuntimeError("boom")


class SleepAgent(HermesAgent):
    """Sub-agent that sleeps (for timeout/cancel tests)."""

    async def _process_task(self, task, input_data, context):
        await asyncio.sleep(30)
        return {}


class SlowAgent(HermesAgent):
    """Sub-agent that blocks briefly (for overload tests)."""

    async def _process_task(self, task, input_data, context):
        await asyncio.sleep(0.5)
        return {"slow": True}


class TestLifecycle:
    def test_legal_path(self):
        task = HermesTask(description="x")
        transition(task, "in_progress")
        assert task.status == "in_progress"
        assert task.started_at is not None
        transition(task, "completed")
        assert task.is_terminal

    def test_illegal_skip_guarded(self):
        with pytest.raises(TransitionError):
            transition(HermesTask(description="x"), "completed")

    def test_terminal_frozen(self):
        task = HermesTask(description="x")
        transition(task, "in_progress")
        transition(task, "completed")
        with pytest.raises(TransitionError):
            transition(task, "in_progress")
        with pytest.raises(TransitionError):
            transition(task, "failed")

    def test_cancel_paths(self):
        assert cancel(HermesTask(description="x")).status == "cancelled"
        t2 = HermesTask(description="y")
        transition(t2, "in_progress")
        assert cancel(t2).status == "cancelled"

    @pytest.mark.asyncio
    async def test_run_with_lifecycle_timeout(self):
        task = HermesTask(description="x")

        async def slow():
            await asyncio.sleep(30)

        with pytest.raises(TimeoutError):
            await run_with_lifecycle(task, slow, timeout=0.05)
        assert task.status == "failed"
        assert "timed out" in task.metadata["error"]


class TestTaskRepresentation:
    def test_round_trip(self):
        task = HermesTask(description="x", type=TaskType.CONTENT, priority=TaskPriority.HIGH,
                          tags=["a"], timeout_seconds=60)
        task.start()
        clone = HermesTask.from_dict(task.to_dict())
        assert clone.id == task.id
        assert clone.type == TaskType.CONTENT
        assert clone.priority == TaskPriority.HIGH
        assert clone.status == "in_progress"
        assert clone.tags == ["a"]
        assert clone.timeout_seconds == 60

    def test_unknown_values_fall_back(self):
        clone = HermesTask.from_dict({"description": "x", "type": "nope", "priority": 99})
        assert clone.type == TaskType.GENERIC
        assert clone.priority == TaskPriority.NORMAL

    def test_state_mapping(self):
        assert HermesTask(description="x").state == TaskState.PENDING
        t = HermesTask(description="x")
        t.start()
        assert t.state == TaskState.EXECUTING


class TestAgentExecution:
    @pytest.mark.asyncio
    async def test_execute_drives_lifecycle(self):
        agent = EchoAgent(HermesAgentConfig(name="echo"))
        task = HermesTask(description="hi", input_data={"v": 1})
        result = await agent.execute(task="hi", input_data={"v": 1}, task_obj=task)
        assert result["success"] is True
        assert result["task_id"] == task.id
        assert result["result"] == {"echo": {"v": 1}}
        assert task.status == "completed"
        assert task.metadata["output"] == {"echo": {"v": 1}}
        assert agent.state == AgentState.IDLE
        assert agent.is_available

    @pytest.mark.asyncio
    async def test_execute_failure_marks_task_and_agent(self):
        agent = BoomAgent(HermesAgentConfig(name="boom", max_retries=1))
        task = HermesTask(description="hi")
        result = await agent.execute(task="hi", task_obj=task)
        assert result["success"] is False
        assert "boom" in result["error"]
        assert task.status == "failed"
        assert agent.state == AgentState.ERROR
        assert not agent.is_available

    @pytest.mark.asyncio
    async def test_execute_enforces_timeout(self):
        agent = SleepAgent(HermesAgentConfig(name="sleepy"))
        task = HermesTask(description="hi", timeout_seconds=1)
        task.timeout_seconds = 0.05
        result = await agent.execute(task="hi", task_obj=task)
        assert result["success"] is False
        assert "timed out" in result["error"]
        assert task.status == "failed"

    @pytest.mark.asyncio
    async def test_execute_cancel_propagates(self):
        agent = SleepAgent(HermesAgentConfig(name="sleepy2"))
        task = HermesTask(description="hi", timeout_seconds=60)
        running = asyncio.create_task(agent.execute(task="hi", task_obj=task))
        await asyncio.sleep(0.05)
        running.cancel()
        with pytest.raises(asyncio.CancelledError):
            await running
        assert task.status == "cancelled"
        assert agent.state == AgentState.IDLE

    @pytest.mark.asyncio
    async def test_execute_without_task_object(self):
        agent = EchoAgent(HermesAgentConfig(name="echo2"))
        result = await agent.execute(task="hi", input_data={"v": 2})
        assert result["success"] is True
        assert result["task_id"]


class TestDelegationInterface:
    def test_busy_agents_not_routed(self):
        router = AgentRouter()
        busy = EchoAgent(HermesAgentConfig(name="busy"))
        busy.state = AgentState.EXECUTING
        idle = EchoAgent(HermesAgentConfig(name="idle"))
        router.register_agent(busy)
        router.register_agent(idle)
        assert router.route_task(HermesTask(description="x")) is idle

    def test_stopped_agents_not_routed(self):
        router = AgentRouter()
        stopped = EchoAgent(HermesAgentConfig(name="stopped"))
        stopped.state = AgentState.STOPPED
        router.register_agent(stopped)
        assert router.route_task(HermesTask(description="x")) is None

    def test_pool_availability(self):
        manager = SubAgentManager()
        agent = EchoAgent(HermesAgentConfig(name="a"))
        manager.register(agent)
        assert manager.get_available() == [agent]
        agent.state = AgentState.EXECUTING
        assert manager.get_available() == []

    @pytest.mark.asyncio
    async def test_delegate_success(self):
        sup = HermesSupervisor()
        sup.register_sub_agent(EchoAgent(HermesAgentConfig(name="w")))
        task = HermesTask(description="do", input_data={"v": 3}, type=TaskType.CONTENT)
        result = await sup.delegate_task(task)
        assert isinstance(result, HermesResult)
        assert result.success is True
        assert result.output == {"echo": {"v": 3}}
        assert task.status == "completed"
        assert task.assigned_agent is not None

    @pytest.mark.asyncio
    async def test_delegate_no_agent(self):
        sup = HermesSupervisor()
        task = HermesTask(description="do")
        result = await sup.delegate_task(task)
        assert result.success is False
        assert "No suitable agent" in result.error
        assert task.status == "failed"

    @pytest.mark.asyncio
    async def test_delegate_failure(self):
        sup = HermesSupervisor()
        sup.register_sub_agent(BoomAgent(HermesAgentConfig(name="b", max_retries=1)))
        task = HermesTask(description="do")
        result = await sup.delegate_task(task)
        assert result.success is False
        assert task.status == "failed"

    @pytest.mark.asyncio
    async def test_execute_parallel(self):
        sup = HermesSupervisor()
        sup.register_sub_agent(EchoAgent(HermesAgentConfig(name="w1")))
        sup.register_sub_agent(EchoAgent(HermesAgentConfig(name="w2")))
        tasks = [HermesTask(description=f"t{i}", input_data={"i": i}) for i in range(2)]
        results = await sup.execute_parallel(tasks)
        assert len(results) == 2
        assert all(r.success for r in results)
        assert all(t.status == "completed" for t in tasks)

    @pytest.mark.asyncio
    async def test_parallel_overload_fails_cleanly(self):
        # More concurrent tasks than idle agents: the excess task fails
        # fast with a clear error instead of double-booking a busy agent.
        sup = HermesSupervisor()
        sup.register_sub_agent(SlowAgent(HermesAgentConfig(name="solo")))
        tasks = [HermesTask(description=f"t{i}", timeout_seconds=60) for i in range(2)]
        results = await sup.execute_parallel(tasks)
        assert len(results) == 2
        assert sum(r.success for r in results) == 1
        failed = next(r for r in results if not r.success)
        assert "No suitable agent" in failed.error


class TestPlanningInterface:
    def test_build_execution_plan_ordering(self):
        planner = TaskPlanner()
        plan = planner.build_execution_plan("ship feature")
        assert len(plan.steps) == 3
        ids = [s.id for s in plan.steps]
        assert plan.steps[0].depends_on == []
        assert plan.steps[1].depends_on == [ids[0]]
        assert plan.steps[2].depends_on == [ids[1]]

        # Walk the plan in dependency order
        seen = []
        while True:
            step = plan.get_next_step()
            if step is None:
                break
            seen.append(step.id)
            step.complete({"ok": True})
        assert seen == ids
        assert plan.progress == 100
        assert plan.to_dict()["status"] == "active"

    def test_build_plan_from_tasks(self):
        planner = TaskPlanner()
        tasks = [
            HermesTask(description="a", assigned_agent="agent-1"),
            HermesTask(description="b"),
        ]
        plan = planner.build_execution_plan("goal", subtasks=tasks, agent_ids=["agent-9"])
        assert [s.id for s in plan.steps] == [tasks[0].id, tasks[1].id]
        assert plan.steps[0].agent_id == "agent-1"
        assert plan.steps[1].agent_id == "agent-9"
        assert plan.steps[1].depends_on == [tasks[0].id]
