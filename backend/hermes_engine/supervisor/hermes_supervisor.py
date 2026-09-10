"""
Hermes Supervisor - Main orchestration agent.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

from ..core.hermes_agent import HermesAgent, HermesAgentConfig, AgentState
from ..core.task import HermesTask, TaskType, TaskPriority
from ..core.result import HermesResult, PlanResult
from ..core.lifecycle import fail as _fail_task
from ..core.lifecycle import begin as _begin_task
from .intent_router import IntentRouter
from .agent_router import AgentRouter

logger = logging.getLogger(__name__)


class HermesSupervisor(HermesAgent):
    """
    Main supervisor agent that orchestrates sub-agents and tasks.
    
    Responsibilities:
    - Intent classification and routing
    - Task decomposition
    - Sub-agent coordination
    - Result aggregation
    """

    def __init__(self, config: Optional[HermesAgentConfig] = None):
        if config is None:
            config = HermesAgentConfig(
                name="hermes-supervisor",
                description="Main orchestration supervisor",
                model="gpt-4",
                tools=["intent_classification", "task_routing"],
            )
        super().__init__(config)
        self._sub_agents: Dict[str, HermesAgent] = {}
        self._intent_router = IntentRouter()
        self._agent_router = AgentRouter()
        self._active_tasks: Dict[str, HermesTask] = {}

    def register_sub_agent(self, agent: HermesAgent) -> None:
        """Register a sub-agent for task delegation."""
        self._sub_agents[agent.agent_id] = agent
        self._agent_router.register_agent(agent)
        logger.info(f"Registered sub-agent: {agent.name} ({agent.agent_id})")

    def unregister_sub_agent(self, agent_id: str) -> bool:
        """Unregister a sub-agent."""
        agent = self._sub_agents.pop(agent_id, None)
        if agent:
            self._agent_router.unregister_agent(agent_id)
            return True
        return False

    async def _process_task(
        self,
        task: str,
        input_data: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Any:
        """Process a task by routing to appropriate sub-agents."""
        # Classify intent
        intent = self._intent_router.classify(task, input_data)
        logger.info(f"Classified intent: {intent}")

        # Find appropriate agent
        agent = self._agent_router.route(intent, input_data)

        if agent:
            # Delegate to sub-agent
            result = await agent.execute(task, input_data, context)
            return result
        else:
            # Process directly
            return await self._execute_directly(task, input_data, context)

    async def _execute_directly(
        self,
        task: str,
        input_data: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Any:
        """Execute task directly when no sub-agent is available."""
        return {
            "task": task,
            "input_data": input_data,
            "status": "processed_by_supervisor",
            "timestamp": self._get_timestamp(),
        }

    async def delegate_task(
        self,
        task: HermesTask,
        agent_id: Optional[str] = None,
    ) -> HermesResult:
        """
        Delegate a task to a specific or auto-selected agent.

        Drives the task lifecycle (pending -> in_progress ->
        completed/failed) around the delegated execution.
        """
        if agent_id:
            agent = self._sub_agents.get(agent_id)
        else:
            agent = self._agent_router.route_task(task)

        if not agent:
            task.metadata["error"] = "No suitable agent found"
            try:
                _begin_task(task)
                _fail_task(task)
            except Exception:
                pass
            return HermesResult(
                task_id=task.id,
                success=False,
                error="No suitable agent found",
            )

        task.assigned_agent = agent.agent_id
        self._active_tasks[task.id] = task

        try:
            result = await agent.execute(
                task=task.description,
                input_data=task.input_data,
                task_obj=task,
            )
            return HermesResult(
                task_id=task.id,
                success=result.get("success", False),
                output=result.get("result"),
                error=result.get("error"),
                agent_id=agent.agent_id,
                agent_name=agent.name,
            )
        finally:
            self._active_tasks.pop(task.id, None)

    async def execute_parallel(
        self,
        tasks: List[HermesTask],
    ) -> List[HermesResult]:
        """Execute multiple tasks in parallel."""
        coros = [self.delegate_task(task) for task in tasks]
        return list(await asyncio.gather(*coros, return_exceptions=False))

    def get_sub_agents(self) -> List[Dict[str, Any]]:
        """Get info about all registered sub-agents."""
        return [
            {
                "agent_id": agent.agent_id,
                "name": agent.name,
                "state": agent.state.value,
            }
            for agent in self._sub_agents.values()
        ]

    def get_progress(self) -> Dict[str, Any]:
        """Get current execution progress."""
        return {
            "active_tasks": len(self._active_tasks),
            "sub_agents": len(self._sub_agents),
            "task_ids": list(self._active_tasks.keys()),
        }

    @staticmethod
    def _get_timestamp() -> str:
        from datetime import datetime
        return datetime.utcnow().isoformat()
