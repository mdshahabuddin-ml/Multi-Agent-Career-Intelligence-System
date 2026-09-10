"""
Agent Router - Routes tasks to appropriate agents.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .intent_router import Intent

if TYPE_CHECKING:
    from ..core.hermes_agent import HermesAgent

logger = logging.getLogger(__name__)


class AgentRouter:
    """
    Routes tasks to agents based on capabilities and intent.
    """

    def __init__(self):
        self._agents: Dict[str, "HermesAgent"] = {}
        self._intent_agents: Dict[Intent, List[str]] = {}

    def register_agent(
        self,
        agent: "HermesAgent",
        intents: Optional[List[Intent]] = None,
    ) -> None:
        """Register an agent with optional intent mappings."""
        self._agents[agent.agent_id] = agent

        if intents:
            for intent in intents:
                self._intent_agents.setdefault(intent, []).append(agent.agent_id)

    def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an agent."""
        if agent_id in self._agents:
            del self._agents[agent_id]
            # Remove from intent mappings
            for intent in list(self._intent_agents.keys()):
                self._intent_agents[intent] = [
                    aid for aid in self._intent_agents[intent]
                    if aid != agent_id
                ]
            return True
        return False

    def route(
        self,
        intent: Intent,
        input_data: Optional[Dict[str, Any]] = None,
    ) -> Optional["HermesAgent"]:
        """
        Route to an agent based on intent.
        
        Args:
            intent: Classified intent
            input_data: Task input data
            
        Returns:
            Best matching agent or None
        """
        # Get agents registered for this intent
        agent_ids = self._intent_agents.get(intent, [])

        # Filter to available agents
        available = [
            self._agents[aid]
            for aid in agent_ids
            if aid in self._agents
        ]

        if available:
            # Return first available (could be smarter with load balancing)
            return available[0]

        # Fallback to any idle agent (busy, stopped, or errored agents
        # must not receive new work)
        idle_agents = [
            agent for agent in self._agents.values()
            if agent.is_available
        ]

        return idle_agents[0] if idle_agents else None

    def route_task(self, task: Any) -> Optional["HermesAgent"]:
        """Route a HermesTask to an appropriate agent."""
        # Simple routing based on task type/tags; only idle agents qualify
        for agent in self._agents.values():
            if agent.is_available:
                return agent
        return None

    def get_agents_for_intent(self, intent: Intent) -> List["HermesAgent"]:
        """Get all agents registered for an intent."""
        agent_ids = self._intent_agents.get(intent, [])
        return [self._agents[aid] for aid in agent_ids if aid in self._agents]

    def get_all_agents(self) -> List[Dict[str, Any]]:
        """Get info about all registered agents."""
        return [
            {
                "agent_id": agent.agent_id,
                "name": agent.name,
                "state": agent.state.value,
            }
            for agent in self._agents.values()
        ]
