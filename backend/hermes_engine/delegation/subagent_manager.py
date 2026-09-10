"""
Sub-Agent Manager - Manages sub-agent lifecycle and coordination.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.hermes_agent import HermesAgent

logger = logging.getLogger(__name__)


class SubAgentManager:
    """
    Manages the lifecycle and coordination of sub-agents.
    """

    def __init__(self):
        self._agents: Dict[str, "HermesAgent"] = {}
        self._pools: Dict[str, List[str]] = {}

    def register(self, agent: "HermesAgent", pool: str = "default") -> None:
        """Register a sub-agent."""
        self._agents[agent.agent_id] = agent
        self._pools.setdefault(pool, []).append(agent.agent_id)
        logger.info(f"Registered sub-agent: {agent.name} in pool '{pool}'")

    def unregister(self, agent_id: str) -> bool:
        """Unregister a sub-agent."""
        if agent_id in self._agents:
            del self._agents[agent_id]
            for pool in self._pools.values():
                if agent_id in pool:
                    pool.remove(agent_id)
            return True
        return False

    def get_agent(self, agent_id: str) -> Optional["HermesAgent"]:
        """Get a sub-agent by ID."""
        return self._agents.get(agent_id)

    def get_pool(self, pool: str) -> List["HermesAgent"]:
        """Get all agents in a pool."""
        agent_ids = self._pools.get(pool, [])
        return [self._agents[aid] for aid in agent_ids if aid in self._agents]

    def get_available(self, pool: str = "default") -> List["HermesAgent"]:
        """Get available agents in a pool (idle agents only)."""
        return [
            agent for agent in self.get_pool(pool)
            if agent.is_available
        ]

    def get_all(self) -> List[Dict[str, Any]]:
        """Get info about all registered agents."""
        return [
            {
                "agent_id": agent.agent_id,
                "name": agent.name,
                "state": agent.state.value,
            }
            for agent in self._agents.values()
        ]

    def create_pool(self, name: str) -> None:
        """Create a new agent pool."""
        if name not in self._pools:
            self._pools[name] = []
