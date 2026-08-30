import logging
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import re

logger = logging.getLogger(__name__)


class SubtaskType(str, Enum):
    WEB_SEARCH = "web_search"
    NEWS_SEARCH = "news_search"
    JOB_MARKET_ANALYSIS = "job_market_analysis"
    COMPANY_RESEARCH = "company_research"
    ACADEMIC_SEARCH = "academic_search"
    SALARY_RESEARCH = "salary_research"
    SKILL_ANALYSIS = "skill_analysis"
    INTERVIEW_PREP = "interview_prep"
    MARKET_TRENDS = "market_trends"
    COMPETITOR_ANALYSIS = "competitor_analysis"


@dataclass
class Subtask:
    """Individual subtask for parallel execution."""
    id: str
    type: SubtaskType
    query: str
    description: str
    priority: int = 1
    parameters: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    status: str = "pending"
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class DecompositionResult:
    """Result of query decomposition."""
    original_query: str
    research_type: str
    subtasks: List[Subtask]
    reasoning: str
    estimated_duration: int  # seconds
    complexity_score: float  # 0-1


class TaskDecomposer:
    """Decompose user queries into parallelizable subtasks."""

    def __init__(self):
        self.name = "task_decomposer"

        self.type_keywords = {
            SubtaskType.WEB_SEARCH: [
                "what is", "how to", "definition", "overview", "guide",
                "tutorial", "explain", "introduction", "basics"
            ],
            SubtaskType.NEWS_SEARCH: [
                "news", "latest", "recent", "update", "announcement",
                "breaking", "trending", "current events"
            ],
            SubtaskType.JOB_MARKET_ANALYSIS: [
                "job market", "hiring", "demand", "employment",
                "career outlook", "job growth", "unemployment", "vacancies"
            ],
            SubtaskType.COMPANY_RESEARCH: [
                "company", "organization", "employer", "workplace",
                "culture", "benefits", "glassdoor", "reviews"
            ],
            SubtaskType.ACADEMIC_SEARCH: [
                "research", "study", "paper", "academic", "journal",
                "publication", "peer-reviewed", "scientific", "analysis"
            ],
            SubtaskType.SALARY_RESEARCH: [
                "salary", "compensation", "pay", "wage", "income",
                "earnings", "remuneration", "benchmark"
            ],
            SubtaskType.SKILL_ANALYSIS: [
                "skill", "competency", "ability", "expertise",
                "proficiency", "qualification", "requirement"
            ],
            SubtaskType.INTERVIEW_PREP: [
                "interview", "question", "prepare", "practice",
                "behavioral", "technical interview", "coding interview"
            ],
            SubtaskType.MARKET_TRENDS: [
                "trend", "future", "forecast", "prediction", "outlook",
                "emerging", "evolution", "direction"
            ],
            SubtaskType.COMPETITOR_ANALYSIS: [
                "competitor", "competition", "alternative", "compare",
                "versus", "vs", "market leader", "peer"
            ],
        }

    async def decompose(
        self,
        query: str,
        research_type: str,
        target_role: Optional[str] = None,
        target_company: Optional[str] = None,
        target_location: Optional[str] = None,
        max_subtasks: int = 8,
    ) -> DecompositionResult:
        """Decompose query into subtasks."""
        logger.info(f"Decomposing query: {query}")

        query_lower = query.lower()
        subtasks = []
        task_id = 0

        # Detect relevant subtask types from query
        detected_types = self._detect_subtask_types(query_lower)

        # Add research-type specific subtasks
        type_subtasks = self._get_type_subtasks(research_type, query, target_role, target_company, target_location)
        for st in type_subtasks:
            detected_types.add(st)

        # Create subtasks for each detected type
        for stype in detected_types:
            if len(subtasks) >= max_subtasks:
                break

            task_id += 1
            subtask = self._create_subtask(
                task_id, stype, query, research_type,
                target_role, target_company, target_location
            )
            if subtask:
                subtasks.append(subtask)

        # Add dependencies (some tasks depend on others)
        subtasks = self._add_dependencies(subtasks)

        # Sort by priority
        subtasks.sort(key=lambda s: s.priority)

        reasoning = self._generate_reasoning(query, detected_types, subtasks)
        complexity = self._calculate_complexity(subtasks)
        duration = self._estimate_duration(subtasks)

        return DecompositionResult(
            original_query=query,
            research_type=research_type,
            subtasks=subtasks,
            reasoning=reasoning,
            estimated_duration=duration,
            complexity_score=complexity,
        )

    def _detect_subtask_types(self, query: str) -> set:
        """Detect which subtask types are relevant to the query."""
        detected = set()

        for stype, keywords in self.type_keywords.items():
            if any(kw in query for kw in keywords):
                detected.add(stype)

        return detected

    def _get_type_subtasks(
        self,
        research_type: str,
        query: str,
        target_role: Optional[str],
        target_company: Optional[str],
        target_location: Optional[str],
    ) -> set:
        """Get subtask types based on research type."""
        type_map = {
            "job_market": {
                SubtaskType.JOB_MARKET_ANALYSIS,
                SubtaskType.SALARY_RESEARCH,
                SubtaskType.SKILL_ANALYSIS,
                SubtaskType.MARKET_TRENDS,
            },
            "company": {
                SubtaskType.COMPANY_RESEARCH,
                SubtaskType.NEWS_SEARCH,
                SubtaskType.COMPETITOR_ANALYSIS,
            },
            "technology": {
                SubtaskType.WEB_SEARCH,
                SubtaskType.ACADEMIC_SEARCH,
                SubtaskType.NEWS_SEARCH,
                SubtaskType.MARKET_TRENDS,
            },
            "career_path": {
                SubtaskType.JOB_MARKET_ANALYSIS,
                SubtaskType.SKILL_ANALYSIS,
                SubtaskType.SALARY_RESEARCH,
                SubtaskType.WEB_SEARCH,
            },
            "skill_analysis": {
                SubtaskType.SKILL_ANALYSIS,
                SubtaskType.JOB_MARKET_ANALYSIS,
                SubtaskType.WEB_SEARCH,
                SubtaskType.ACADEMIC_SEARCH,
            },
            "salary": {
                SubtaskType.SALARY_RESEARCH,
                SubtaskType.JOB_MARKET_ANALYSIS,
                SubtaskType.COMPANY_RESEARCH,
            },
            "interview_prep": {
                SubtaskType.INTERVIEW_PREP,
                SubtaskType.COMPANY_RESEARCH,
                SubtaskType.SKILL_ANALYSIS,
            },
        }

        return type_map.get(research_type, {SubtaskType.WEB_SEARCH, SubtaskType.NEWS_SEARCH})

    def _create_subtask(
        self,
        task_id: int,
        stype: SubtaskType,
        query: str,
        research_type: str,
        target_role: Optional[str],
        target_company: Optional[str],
        target_location: Optional[str],
    ) -> Optional[Subtask]:
        """Create a subtask for the given type."""
        templates = {
            SubtaskType.WEB_SEARCH: {
                "query_template": "{query}",
                "description": "General web search for overview information",
                "priority": 1,
            },
            SubtaskType.NEWS_SEARCH: {
                "query_template": "{query} latest news 2024",
                "description": "Search for recent news and updates",
                "priority": 2,
            },
            SubtaskType.JOB_MARKET_ANALYSIS: {
                "query_template": "{target_role or query} job market trends demand 2024",
                "description": "Analyze job market trends and demand",
                "priority": 1,
            },
            SubtaskType.COMPANY_RESEARCH: {
                "query_template": "{target_company or query} company profile culture benefits",
                "description": "Research company profile and culture",
                "priority": 1,
            },
            SubtaskType.ACADEMIC_SEARCH: {
                "query_template": "{query} research paper study",
                "description": "Search academic papers and research",
                "priority": 2,
            },
            SubtaskType.SALARY_RESEARCH: {
                "query_template": "{target_role or query} salary compensation 2024 {target_location or ''}",
                "description": "Research salary benchmarks",
                "priority": 2,
            },
            SubtaskType.SKILL_ANALYSIS: {
                "query_template": "{target_role or query} required skills competencies 2024",
                "description": "Analyze required skills and competencies",
                "priority": 1,
            },
            SubtaskType.INTERVIEW_PREP: {
                "query_template": "{target_company or target_role or query} interview questions preparation",
                "description": "Find interview questions and preparation tips",
                "priority": 1,
            },
            SubtaskType.MARKET_TRENDS: {
                "query_template": "{query} trends forecast 2024 2025",
                "description": "Analyze market trends and forecasts",
                "priority": 2,
            },
            SubtaskType.COMPETITOR_ANALYSIS: {
                "query_template": "{target_company or query} competitors alternatives comparison",
                "description": "Analyze competitors and alternatives",
                "priority": 3,
            },
        }

        template = templates.get(stype)
        if not template:
            return None

        # Format query template
        formatted_query = template["query_template"].format(
            query=query,
            target_role=target_role or "",
            target_company=target_company or "",
            target_location=target_location or "",
        ).strip()

        return Subtask(
            id=f"subtask_{task_id}_{stype.value}",
            type=stype,
            query=formatted_query,
            description=template["description"],
            priority=template["priority"],
            parameters={
                "research_type": research_type,
                "target_role": target_role,
                "target_company": target_company,
                "target_location": target_location,
            },
        )

    def _add_dependencies(self, subtasks: List[Subtask]) -> List[Subtask]:
        """Add dependencies between subtasks."""
        # Map of types that should run before others
        dependency_map = {
            SubtaskType.WEB_SEARCH: [],  # No dependencies
            SubtaskType.NEWS_SEARCH: [],  # No dependencies
            SubtaskType.JOB_MARKET_ANALYSIS: [SubtaskType.WEB_SEARCH],
            SubtaskType.COMPANY_RESEARCH: [SubtaskType.WEB_SEARCH],
            SubtaskType.ACADEMIC_SEARCH: [SubtaskType.WEB_SEARCH],
            SubtaskType.SALARY_RESEARCH: [SubtaskType.JOB_MARKET_ANALYSIS, SubtaskType.WEB_SEARCH],
            SubtaskType.SKILL_ANALYSIS: [SubtaskType.JOB_MARKET_ANALYSIS, SubtaskType.WEB_SEARCH],
            SubtaskType.INTERVIEW_PREP: [SubtaskType.COMPANY_RESEARCH, SubtaskType.SKILL_ANALYSIS],
            SubtaskType.MARKET_TRENDS: [SubtaskType.WEB_SEARCH, SubtaskType.NEWS_SEARCH],
            SubtaskType.COMPETITOR_ANALYSIS: [SubtaskType.COMPANY_RESEARCH, SubtaskType.WEB_SEARCH],
        }

        # Create lookup
        task_by_type = {st.type: st.id for st in subtasks}

        for subtask in subtasks:
            deps = dependency_map.get(subtask.type, [])
            subtask.dependencies = [task_by_type[dep] for dep in deps if dep in task_by_type]

        return subtasks

    def _generate_reasoning(
        self,
        query: str,
        detected_types: set,
        subtasks: List[Subtask],
    ) -> str:
        """Generate reasoning for decomposition."""
        parts = [
            f"Query '{query}' decomposed into {len(subtasks)} subtasks.",
            f"Detected task types: {', '.join(t.value for t in detected_types)}.",
        ]

        # Add specific reasoning
        if SubtaskType.JOB_MARKET_ANALYSIS in detected_types:
            parts.append("Job market analysis prioritized for career intelligence.")
        if SubtaskType.COMPANY_RESEARCH in detected_types:
            parts.append("Company research included for employer insights.")
        if SubtaskType.ACADEMIC_SEARCH in detected_types:
            parts.append("Academic search added for evidence-based findings.")

        return " ".join(parts)

    def _calculate_complexity(self, subtasks: List[Subtask]) -> float:
        """Calculate complexity score 0-1."""
        base = len(subtasks) / 10.0  # More tasks = more complex
        has_deps = any(s.dependencies for s in subtasks)
        if has_deps:
            base += 0.2
        return min(base, 1.0)

    def _estimate_duration(self, subtasks: List[Subtask]) -> int:
        """Estimate total duration in seconds."""
        # Parallel execution: max of sequential chains
        # For simplicity, estimate based on count and dependencies
        base_time = 30  # seconds per task
        sequential_chains = self._find_longest_chain(subtasks)
        return sequential_chains * base_time

    def _find_longest_chain(self, subtasks: List[Subtask]) -> int:
        """Find longest dependency chain."""
        task_map = {st.id: st for st in subtasks}
        max_chain = 1

        def chain_length(task_id: str, visited: set) -> int:
            if task_id in visited:
                return 0
            visited.add(task_id)
            task = task_map.get(task_id)
            if not task or not task.dependencies:
                return 1
            return 1 + max(chain_length(dep, visited.copy()) for dep in task.dependencies)

        for st in subtasks:
            max_chain = max(max_chain, chain_length(st.id, set()))

        return max_chain