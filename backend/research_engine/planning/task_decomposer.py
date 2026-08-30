import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum as PyEnum

from backend.research_engine.state.research_context import (
    ResearchTask, ResearchPlan, ResearchType, ResearchClaim, ResearchEvidence,
    SourceMetadata
)

logger = logging.getLogger(__name__)


class DecompositionStrategy(str, PyEnum):
    """Strategies for task decomposition."""
    BREADTH_FIRST = "breadth_first"  # Cover all agent types
    DEPTH_FIRST = "depth_first"  # Focus on most relevant agent type
    PARALLEL = "parallel"  # Run all tasks in parallel
    SEQUENTIAL = "sequential"  # Run tasks sequentially


@dataclass
class DecompositionRule:
    """Rule for decomposing a query into tasks."""
    research_type: ResearchType
    agent_type: str
    query_template: str
    description_template: str
    priority: int
    conditions: Dict[str, Any] = field(default_factory=dict)
    required_params: List[str] = field(default_factory=list)


# Default decomposition rules for each research type
DEFAULT_DECOMPOSITION_RULES = [
    # Job Market Research
    DecompositionRule(
        research_type=ResearchType.JOB_MARKET,
        agent_type="job_market",
        query_template="{query} job market trends 2024 demand salary",
        description_template="Analyze job market trends and demand for {query}",
        priority=1,
    ),
    DecompositionRule(
        research_type=ResearchType.JOB_MARKET,
        agent_type="web",
        query_template="{query} salary trends 2024 compensation",
        description_template="Research salary trends and compensation for {query}",
        priority=2,
    ),
    DecompositionRule(
        research_type=ResearchType.JOB_MARKET,
        agent_type="news",
        query_template="{query} hiring news layoffs 2024",
        description_template="Find recent hiring news and market movements for {query}",
        priority=3,
    ),
    DecompositionRule(
        research_type=ResearchType.JOB_MARKET,
        agent_type="company",
        query_template="top companies hiring {query} 2024",
        description_template="Identify top companies hiring for {query} roles",
        priority=4,
        conditions={"target_company": None},
    ),

    # Company Research
    DecompositionRule(
        research_type=ResearchType.COMPANY,
        agent_type="company",
        query_template="{target_company} company profile culture benefits tech stack",
        description_template="Analyze {target_company} company profile, culture, and tech stack",
        priority=1,
        required_params=["target_company"],
    ),
    DecompositionRule(
        research_type=ResearchType.COMPANY,
        agent_type="web",
        query_template="{target_company} reviews glassdoor blind employee experience",
        description_template="Research employee reviews and experiences at {target_company}",
        priority=2,
        required_params=["target_company"],
    ),
    DecompositionRule(
        research_type=ResearchType.COMPANY,
        agent_type="news",
        query_template="{target_company} news funding acquisition 2024",
        description_template="Find recent news about {target_company}",
        priority=3,
        required_params=["target_company"],
    ),
    DecompositionRule(
        research_type=ResearchType.COMPANY,
        agent_type="job_market",
        query_template="{target_company} hiring jobs open positions",
        description_template="Analyze current job openings at {target_company}",
        priority=4,
        required_params=["target_company"],
    ),

    # Technology Research
    DecompositionRule(
        research_type=ResearchType.TECHNOLOGY,
        agent_type="web",
        query_template="{query} technology trends 2024 adoption",
        description_template="Research technology trends and adoption for {query}",
        priority=1,
    ),
    DecompositionRule(
        research_type=ResearchType.TECHNOLOGY,
        agent_type="academic",
        query_template="{query} research paper survey state of the art",
        description_template="Find academic research on {query}",
        priority=2,
    ),
    DecompositionRule(
        research_type=ResearchType.TECHNOLOGY,
        agent_type="news",
        query_template="{query} technology news release update 2024",
        description_template="Find recent technology news for {query}",
        priority=3,
    ),
    DecompositionRule(
        research_type=ResearchType.TECHNOLOGY,
        agent_type="job_market",
        query_template="{query} skills demand jobs required",
        description_template="Analyze skill demand for {query} in job market",
        priority=4,
    ),

    # Career Path Research
    DecompositionRule(
        research_type=ResearchType.CAREER_PATH,
        agent_type="job_market",
        query_template="{target_role} career path progression salary trajectory",
        description_template="Analyze career progression for {target_role}",
        priority=1,
        required_params=["target_role"],
    ),
    DecompositionRule(
        research_type=ResearchType.CAREER_PATH,
        agent_type="web",
        query_template="{target_role} skills required experience promotion",
        description_template="Research required skills and experience for {target_role} advancement",
        priority=2,
        required_params=["target_role"],
    ),
    DecompositionRule(
        research_type=ResearchType.CAREER_PATH,
        agent_type="company",
        query_template="companies hiring {target_role} career growth",
        description_template="Find companies with strong {target_role} career growth",
        priority=3,
        required_params=["target_role"],
    ),

    # Skill Analysis Research
    DecompositionRule(
        research_type=ResearchType.SKILL_ANALYSIS,
        agent_type="job_market",
        query_template="{query} skill demand market value salary premium",
        description_template="Analyze market demand and value for {query} skill",
        priority=1,
    ),
    DecompositionRule(
        research_type=ResearchType.SKILL_ANALYSIS,
        agent_type="web",
        query_template="{query} learning resources certification course tutorial",
        description_template="Find learning resources for {query}",
        priority=2,
    ),
    DecompositionRule(
        research_type=ResearchType.SKILL_ANALYSIS,
        agent_type="academic",
        query_template="{query} skill assessment measurement competency",
        description_template="Find academic research on {query} skill assessment",
        priority=3,
    ),

    # Salary Research
    DecompositionRule(
        research_type=ResearchType.SALARY,
        agent_type="job_market",
        query_template="{target_role} salary compensation 2024 {target_location}",
        description_template="Analyze salary benchmarks for {target_role}",
        priority=1,
        required_params=["target_role"],
    ),
    DecompositionRule(
        research_type=ResearchType.SALARY,
        agent_type="web",
        query_template="{target_role} salary negotiation benefits equity {target_location}",
        description_template="Research salary negotiation and total compensation for {target_role}",
        priority=2,
        required_params=["target_role"],
    ),

    # Interview Prep Research
    DecompositionRule(
        research_type=ResearchType.INTERVIEW_PREP,
        agent_type="web",
        query_template="{target_role} interview questions technical behavioral 2024",
        description_template="Find common interview questions for {target_role}",
        priority=1,
        required_params=["target_role"],
    ),
    DecompositionRule(
        research_type=ResearchType.INTERVIEW_PREP,
        agent_type="company",
        query_template="{target_company} interview process questions {target_role}",
        description_template="Research interview process at {target_company} for {target_role}",
        priority=2,
        required_params=["target_company", "target_role"],
    ),

    # General Research
    DecompositionRule(
        research_type=ResearchType.GENERAL,
        agent_type="web",
        query_template="{query}",
        description_template="General web research on {query}",
        priority=1,
    ),
    DecompositionRule(
        research_type=ResearchType.GENERAL,
        agent_type="news",
        query_template="{query} news 2024",
        description_template="Recent news on {query}",
        priority=2,
    ),
]


class TaskDecomposer:
    """Decompose research queries into executable tasks."""

    def __init__(self, custom_rules: Optional[List[DecompositionRule]] = None):
        self.rules = DEFAULT_DECOMPOSITION_RULES
        if custom_rules:
            self.rules.extend(custom_rules)

    def decompose(
        self,
        query: str,
        research_type: ResearchType,
        target_role: Optional[str] = None,
        target_company: Optional[str] = None,
        target_location: Optional[str] = None,
        max_sources: int = 10,
        timeout_seconds: int = 300,
        strategy: DecompositionStrategy = DecompositionStrategy.PARALLEL,
    ) -> ResearchPlan:
        """Decompose a research query into a plan with tasks."""
        logger.info(f"Decomposing query: {query} (type: {research_type.value})")

        plan = ResearchPlan(
            research_id=0,  # Will be set later
            query=query,
            research_type=research_type,
            max_sources=max_sources,
            timeout_seconds=timeout_seconds,
            target_role=target_role,
            target_company=target_company,
            target_location=target_location,
        )

        # Filter applicable rules
        applicable_rules = self._filter_rules(
            research_type, target_role, target_company, target_location
        )

        # Create tasks from rules
        for i, rule in enumerate(applicable_rules):
            task = self._create_task_from_rule(rule, query, target_role, target_company, target_location, i)
            plan.tasks.append(task)

        # Adjust priorities based on strategy
        self._adjust_priorities(plan, strategy)

        logger.info(f"Created plan with {len(plan.tasks)} tasks")
        return plan

    def _filter_rules(
        self,
        research_type: ResearchType,
        target_role: Optional[str],
        target_company: Optional[str],
        target_location: Optional[str],
    ) -> List[DecompositionRule]:
        """Filter rules applicable to the research context."""
        applicable = []

        for rule in self.rules:
            if rule.research_type != research_type:
                continue

            # Check required params
            missing_params = []
            if "target_role" in rule.required_params and not target_role:
                missing_params.append("target_role")
            if "target_company" in rule.required_params and not target_company:
                missing_params.append("target_company")
            if "target_location" in rule.required_params and not target_location:
                missing_params.append("target_location")

            if missing_params:
                continue

            # Check conditions
            conditions_met = True
            for key, value in rule.conditions.items():
                if key == "target_company" and value is None and not target_company:
                    conditions_met = False
                    break
            if not conditions_met:
                continue

            applicable.append(rule)

        # Sort by priority
        applicable.sort(key=lambda r: r.priority)
        return applicable

    def _create_task_from_rule(
        self,
        rule: DecompositionRule,
        query: str,
        target_role: Optional[str],
        target_company: Optional[str],
        target_location: Optional[str],
        index: int,
    ) -> ResearchTask:
        """Create a research task from a decomposition rule."""
        # Format query template
        formatted_query = rule.query_template.format(
            query=query,
            target_role=target_role or "",
            target_company=target_company or "",
            target_location=target_location or "",
        ).strip()

        # Format description
        formatted_description = rule.description_template.format(
            query=query,
            target_role=target_role or "",
            target_company=target_company or "",
            target_location=target_location or "",
        ).strip()

        return ResearchTask(
            id=f"task_{index}",
            description=formatted_description,
            agent_type=rule.agent_type,
            query=formatted_query,
            priority=rule.priority,
        )

    def _adjust_priorities(self, plan: ResearchPlan, strategy: DecompositionStrategy):
        """Adjust task priorities based on strategy."""
        if strategy == DecompositionStrategy.BREADTH_FIRST:
            # Ensure all agent types are represented with at least one high-priority task
            agent_types_seen = set()
            for task in plan.tasks:
                if task.agent_type not in agent_types_seen:
                    agent_types_seen.add(task.agent_type)
                    task.priority = 1

        elif strategy == DecompositionStrategy.DEPTH_FIRST:
            # Prioritize the first task (most relevant agent type)
            if plan.tasks:
                plan.tasks[0].priority = 1
                for i, task in enumerate(plan.tasks[1:], 1):
                    task.priority = i + 1

        elif strategy == DecompositionStrategy.PARALLEL:
            # All tasks same priority for parallel execution
            for task in plan.tasks:
                task.priority = 1

        elif strategy == DecompositionStrategy.SEQUENTIAL:
            # Sequential by original priority
            pass  # Already sorted

        # Re-sort by priority
        plan.tasks.sort(key=lambda t: t.priority)


class ResearchPlanner:
    """High-level research planner with advanced features."""

    def __init__(self, decomposer: Optional[TaskDecomposer] = None):
        self.decomposer = decomposer or TaskDecomposer()

    async def create_plan(
        self,
        research_id: int,
        query: str,
        research_type: ResearchType,
        max_sources: int = 10,
        timeout_seconds: int = 300,
        target_role: Optional[str] = None,
        target_company: Optional[str] = None,
        target_location: Optional[str] = None,
        strategy: DecompositionStrategy = DecompositionStrategy.PARALLEL,
    ) -> ResearchPlan:
        """Create a research plan."""
        plan = self.decomposer.decompose(
            query=query,
            research_type=research_type,
            target_role=target_role,
            target_company=target_company,
            target_location=target_location,
            max_sources=max_sources,
            timeout_seconds=timeout_seconds,
            strategy=strategy,
        )
        plan.research_id = research_id
        return plan

    async def refine_plan(
        self,
        plan: ResearchPlan,
        intermediate_results: Dict[str, Any],
    ) -> ResearchPlan:
        """Refine plan based on intermediate results (adaptive planning)."""
        # This would add/remove/modify tasks based on what was found
        # For now, return unchanged plan
        return plan

    def estimate_duration(self, plan: ResearchPlan) -> float:
        """Estimate total execution time in seconds."""
        # Rough estimates per agent type
        agent_times = {
            "web": 5,
            "news": 3,
            "job_market": 8,
            "company": 5,
            "academic": 10,
        }

        total = 0
        for task in plan.tasks:
            total += agent_times.get(task.agent_type, 5)

        # Add overhead
        total *= 1.2

        return min(total, plan.timeout_seconds)