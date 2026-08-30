import logging
import asyncio
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod

from backend.models import Research, ResearchStatus, ResearchType, User
from backend.providers.search import SearchProvider, SearchConfig, SearchResult, get_search_registry

logger = logging.getLogger(__name__)


class ResearchPhase(str, Enum):
    CREATED = "created"
    PLANNING = "planning"
    RESEARCHING = "researching"
    COLLECTING_EVIDENCE = "collecting_evidence"
    VERIFYING = "verifying"
    ANALYZING = "analyzing"
    SYNTHESIZING = "synthesizing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ResearchTask:
    """Individual research task."""
    id: str
    description: str
    agent_type: str  # web, news, job_market, company, academic
    query: str
    priority: int = 1
    status: str = "pending"
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    sources: List[Dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None


@dataclass
class ResearchPlan:
    """Research plan with tasks."""
    research_id: int
    query: str
    research_type: ResearchType
    tasks: List[ResearchTask] = field(default_factory=list)
    max_sources: int = 10
    timeout_seconds: int = 300
    created_at: datetime = field(default_factory=datetime.utcnow)


class ResearchAgent(ABC):
    """Base class for all research agents."""

    def __init__(self, name: str, search_provider: SearchProvider, source_type: str):
        self.name = name
        self.search_provider = search_provider
        self.source_type = source_type

    @abstractmethod
    async def execute(self, task: ResearchTask) -> Dict[str, Any]:
        """Execute the research task."""
        pass

    async def search(self, query: str, limit: int = 10, recency_days: Optional[int] = None) -> List[Dict[str, Any]]:
        """Search for sources using the configured search provider."""
        config = SearchConfig(
            query=query,
            limit=limit,
            source_type=self.source_type,
            recency_days=recency_days,
        )
        results = await self.search_provider.search(config)
        return [self._result_to_dict(r) for r in results]

    def _result_to_dict(self, result: SearchResult) -> Dict[str, Any]:
        return {
            "url": result.url,
            "title": result.title,
            "snippet": result.snippet,
            "source_type": result.source_type,
            "published_date": result.published_date,
            "author": result.author,
            "domain": result.domain,
            "credibility": result.credibility,
            "relevance": result.relevance,
            "metadata": result.metadata,
        }


class WebResearcher(ResearchAgent):
    """Research agent for web search."""

    def __init__(self, search_provider: SearchProvider):
        super().__init__("web_researcher", search_provider, "web")

    async def execute(self, task: ResearchTask) -> Dict[str, Any]:
        logger.info(f"Web researcher executing: {task.query}")
        sources = await self.search(task.query, limit=5)
        return {
            "agent": self.name,
            "query": task.query,
            "sources": sources,
            "summary": f"Found {len(sources)} web sources for '{task.query}'",
        }


class NewsResearcher(ResearchAgent):
    """Research agent for news search."""

    def __init__(self, search_provider: SearchProvider):
        super().__init__("news_researcher", search_provider, "news")

    async def execute(self, task: ResearchTask) -> Dict[str, Any]:
        logger.info(f"News researcher executing: {task.query}")
        sources = await self.search(task.query, limit=5, recency_days=30)
        return {
            "agent": self.name,
            "query": task.query,
            "sources": sources,
            "summary": f"Found {len(sources)} news sources for '{task.query}'",
        }


class JobMarketResearcher(ResearchAgent):
    """Research agent for job market trends."""

    def __init__(self, search_provider: SearchProvider):
        super().__init__("job_market_researcher", search_provider, "job_market")

    async def execute(self, task: ResearchTask) -> Dict[str, Any]:
        logger.info(f"Job market researcher executing: {task.query}")
        sources = await self.search(task.query, limit=5, recency_days=90)
        return {
            "agent": self.name,
            "query": task.query,
            "sources": sources,
            "summary": f"Found {len(sources)} job market sources for '{task.query}'",
        }


class CompanyResearcher(ResearchAgent):
    """Research agent for company analysis."""

    def __init__(self, search_provider: SearchProvider):
        super().__init__("company_researcher", search_provider, "company")

    async def execute(self, task: ResearchTask) -> Dict[str, Any]:
        logger.info(f"Company researcher executing: {task.query}")
        sources = await self.search(task.query, limit=5)
        return {
            "agent": self.name,
            "query": task.query,
            "sources": sources,
            "summary": f"Found {len(sources)} company sources for '{task.query}'",
        }


class AcademicResearcher(ResearchAgent):
    """Research agent for academic papers."""

    def __init__(self, search_provider: SearchProvider):
        super().__init__("academic_researcher", search_provider, "academic")

    async def execute(self, task: ResearchTask) -> Dict[str, Any]:
        logger.info(f"Academic researcher executing: {task.query}")
        sources = await self.search(task.query, limit=5)
        return {
            "agent": self.name,
            "query": task.query,
            "sources": sources,
            "summary": f"Found {len(sources)} academic sources for '{task.query}'",
        }


class ResearchPlanner:
    """Plan research tasks based on query and type."""

    def __init__(self):
        self.name = "research_planner"

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
    ) -> ResearchPlan:
        """Create a research plan with tasks for different agent types."""
        logger.info(f"Creating research plan for: {query}")

        plan = ResearchPlan(
            research_id=research_id,
            query=query,
            research_type=research_type,
            max_sources=max_sources,
            timeout_seconds=timeout_seconds,
        )

        # Define tasks based on research type
        task_configs = self._get_task_configs(research_type, query, target_role, target_company, target_location)

        for i, config in enumerate(task_configs):
            task = ResearchTask(
                id=f"task_{research_id}_{i}",
                description=config["description"],
                agent_type=config["agent_type"],
                query=config["query"],
                priority=config.get("priority", 1),
            )
            plan.tasks.append(task)

        logger.info(f"Created plan with {len(plan.tasks)} tasks")
        return plan

    def _get_task_configs(
        self,
        research_type: ResearchType,
        query: str,
        target_role: Optional[str],
        target_company: Optional[str],
        target_location: Optional[str],
    ) -> List[Dict[str, Any]]:
        """Get task configurations based on research type."""
        base_configs = []

        if research_type == ResearchType.JOB_MARKET:
            base_configs = [
                {"agent_type": "job_market", "query": f"{query} job market trends 2024", "description": "Analyze job market trends", "priority": 1},
                {"agent_type": "web", "query": f"{query} salary trends 2024", "description": "Research salary trends", "priority": 2},
                {"agent_type": "news", "query": f"{query} hiring news", "description": "Find recent hiring news", "priority": 3},
            ]
        elif research_type == ResearchType.COMPANY:
            base_configs = [
                {"agent_type": "company", "query": f"{target_company or query} company profile culture", "description": "Analyze company profile", "priority": 1},
                {"agent_type": "web", "query": f"{target_company or query} reviews glassdoor", "description": "Research company reviews", "priority": 2},
                {"agent_type": "news", "query": f"{target_company or query} news", "description": "Find recent company news", "priority": 3},
            ]
        elif research_type == ResearchType.TECHNOLOGY:
            base_configs = [
                {"agent_type": "web", "query": f"{query} technology trends 2024", "description": "Research technology trends", "priority": 1},
                {"agent_type": "academic", "query": f"{query} research paper", "description": "Find academic research", "priority": 2},
                {"agent_type": "news", "query": f"{query} technology news", "description": "Find technology news", "priority": 3},
            ]
        elif research_type == ResearchType.CAREER_PATH:
            base_configs = [
                {"agent_type": "job_market", "query": f"{target_role or query} career path progression", "description": "Analyze career progression", "priority": 1},
                {"agent_type": "web", "query": f"{target_role or query} skills required", "description": "Research required skills", "priority": 2},
            ]
        elif research_type == ResearchType.SKILL_ANALYSIS:
            base_configs = [
                {"agent_type": "job_market", "query": f"{query} skill demand", "description": "Analyze skill demand", "priority": 1},
                {"agent_type": "web", "query": f"{query} learning resources", "description": "Find learning resources", "priority": 2},
            ]
        else:
            # GENERAL
            base_configs = [
                {"agent_type": "web", "query": query, "description": "General web research", "priority": 1},
                {"agent_type": "news", "query": f"{query} news", "description": "Recent news", "priority": 2},
            ]

        return base_configs


class ResearchSupervisor:
    """Supervise and orchestrate the research workflow."""

    def __init__(self, search_provider: Optional[SearchProvider] = None):
        self.name = "research_supervisor"
        self.planner = ResearchPlanner()

        # Use provided search provider or get default from registry
        if search_provider is None:
            registry = get_search_registry()
            provider_types = registry.list_providers()
            for provider_type in provider_types:
                provider_class = registry.get_provider_class(provider_type)
                if provider_class:
                    try:
                        # Try to instantiate with default config (may fail if API key required)
                        search_provider = provider_class()
                        break
                    except TypeError:
                        # Provider requires API key, try next
                        continue

        # If still no provider, use mock
        if search_provider is None:
            from backend.providers.search.mock import MockSearchProvider
            search_provider = MockSearchProvider()

        self.search_provider = search_provider

        # Initialize agents with the search provider
        self.agents = {
            "web": WebResearcher(search_provider),
            "news": NewsResearcher(search_provider),
            "job_market": JobMarketResearcher(search_provider),
            "company": CompanyResearcher(search_provider),
            "academic": AcademicResearcher(search_provider),
        }

    async def execute_research(
        self,
        research: Research,
        db_session,
    ) -> Research:
        """Execute the full research workflow."""
        logger.info(f"Starting research #{research.id}: {research.query}")

        # Update status to planning
        research.status = ResearchStatus.PLANNING
        research.started_at = datetime.utcnow()
        db_session.commit()

        # Create plan
        plan = await self.planner.create_plan(
            research_id=research.id,
            query=research.query,
            research_type=research.research_type,
            max_sources=research.max_sources,
            timeout_seconds=research.timeout_seconds,
            target_role=research.target_role,
            target_company=research.target_company,
            target_location=research.target_location,
        )

        research.research_plan = {
            "tasks": [
                {
                    "id": t.id,
                    "description": t.description,
                    "agent_type": t.agent_type,
                    "query": t.query,
                    "priority": t.priority,
                }
                for t in plan.tasks
            ]
        }
        research.status = ResearchStatus.RESEARCHING
        db_session.commit()

        # Execute tasks in parallel by priority
        all_sources = []
        for task in sorted(plan.tasks, key=lambda t: t.priority):
            task.status = "running"
            agent = self.agents.get(task.agent_type)
            if not agent:
                task.status = "failed"
                task.error = f"No agent for type: {task.agent_type}"
                continue

            try:
                result = await agent.execute(task)
                task.status = "completed"
                task.result = result
                task.completed_at = datetime.utcnow()
                if result.get("sources"):
                    all_sources.extend(result["sources"])
                    task.sources = result["sources"]
            except Exception as e:
                logger.error(f"Task {task.id} failed: {e}")
                task.status = "failed"
                task.error = str(e)

        # Update research with collected sources
        research.status = ResearchStatus.COLLECTING_EVIDENCE
        research.sources = all_sources
        research.source_count = len(all_sources)
        db_session.commit()

        logger.info(f"Research #{research.id} collected {len(all_sources)} sources")
        return research