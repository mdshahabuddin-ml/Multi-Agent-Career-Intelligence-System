"""
Delegation module initialization.
"""

from .subagent_manager import SubAgentManager
from .parallel_executor import ParallelExecutor
from .task_router import TaskRouter

__all__ = [
    "SubAgentManager",
    "ParallelExecutor",
    "TaskRouter",
]
