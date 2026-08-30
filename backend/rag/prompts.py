from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum as PyEnum
import logging

logger = logging.getLogger(__name__)


class PromptType(str, PyEnum):
    """Types of RAG prompts."""
    QUESTION_ANSWERING = "question_answering"
    SUMMARIZATION = "summarization"
    COMPARISON = "comparison"
    ANALYSIS = "analysis"
    RECOMMENDATION = "recommendation"
    EXTRACTION = "extraction"
    FACT_CHECKING = "fact_checking"
    CONVERSATIONAL = "conversational"


@dataclass
class PromptTemplate:
    """A prompt template with variables."""
    name: str
    type: PromptType
    system_prompt: str
    user_prompt_template: str
    variables: List[str] = field(default_factory=list)
    examples: List[Dict[str, str]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def format(self, **kwargs) -> Dict[str, str]:
        """Format the prompt with variables."""
        # Check required variables
        for var in self.variables:
            if var not in kwargs:
                raise ValueError(f"Missing required variable: {var}")

        system = self.system_prompt.format(**kwargs)
        user = self.user_prompt_template.format(**kwargs)

        return {
            "system": system,
            "user": user,
        }


class PromptManager:
    """Manage and render prompt templates."""

    def __init__(self):
        self._templates: Dict[str, PromptTemplate] = {}
        self._register_default_templates()

    def _register_default_templates(self):
        """Register default RAG prompt templates."""

        # Question Answering
        self.register(PromptTemplate(
            name="qa_standard",
            type=PromptType.QUESTION_ANSWERING,
            system_prompt="""You are a helpful AI assistant that answers questions based on provided context.
Your task is to answer the user's question using ONLY the information from the provided sources.
If the context doesn't contain enough information to answer, say so clearly.
Always cite your sources using the citation format provided.
Be concise but thorough. If multiple sources provide conflicting information, acknowledge this.""",
            user_prompt_template="""Context:
{context}

Question: {question}

Instructions:
- Answer based only on the provided context
- Cite sources using [1], [2], etc.
- If information is not in context, say "I don't have enough information to answer this question."
- Be specific and cite relevant sources""",
            variables=["context", "question"],
        ))

        # QA with citations
        self.register(PromptTemplate(
            name="qa_with_citations",
            type=PromptType.QUESTION_ANSWERING,
            system_prompt="""You are an expert research assistant. Answer questions using the provided sources.
Always include inline citations in your response using the format [1], [2], etc.
Each citation should correspond to the numbered sources provided.
If sources conflict, mention the conflict.
If the answer cannot be found in the sources, state this clearly.""",
            user_prompt_template="""Sources:
{sources}

Question: {question}

Provide a well-structured answer with inline citations.""",
            variables=["sources", "question"],
        ))

        # Summarization
        self.register(PromptTemplate(
            name="summarize_sources",
            type=PromptType.SUMMARIZATION,
            system_prompt="""You are an expert at synthesizing information from multiple sources.
Create a clear, concise summary that captures the key points from all provided sources.
Organize by themes or topics. Mention any conflicting information.
Include citations for key claims.""",
            user_prompt_template="""Sources:
{sources}

Task: Create a comprehensive summary of the key findings from these sources.
Organize by theme. Include citations for important claims.""",
            variables=["sources"],
        ))

        # Comparison
        self.register(PromptTemplate(
            name="compare_entities",
            type=PromptType.COMPARISON,
            system_prompt="""You are an expert analyst. Compare the given entities (companies, roles, technologies, etc.)
based on the provided sources. Structure your comparison clearly with specific criteria.
Highlight similarities, differences, advantages, and disadvantages.
Cite sources for each comparison point.""",
            user_prompt_template="""Sources:
{sources}

Entities to compare: {entities}
Comparison criteria: {criteria}

Provide a structured comparison with citations.""",
            variables=["sources", "entities", "criteria"],
        ))

        # Analysis
        self.register(PromptTemplate(
            name="analyze_trends",
            type=PromptType.ANALYSIS,
            system_prompt="""You are a market analyst. Analyze the provided sources to identify trends, patterns,
and insights. Look for: emerging trends, market shifts, skill demands, salary changes,
technology adoption, company strategies.
Structure your analysis with clear sections. Cite evidence for each insight.""",
            user_prompt_template="""Sources:
{sources}

Analysis focus: {focus}
Time period: {time_period}

Provide a structured trend analysis with supporting evidence.""",
            variables=["sources", "focus", "time_period"],
        ))

        # Recommendation
        self.register(PromptTemplate(
            name="generate_recommendations",
            type=PromptType.RECOMMENDATION,
            system_prompt="""You are a career advisor. Based on the provided research, generate actionable
recommendations tailored to the user's profile and goals.
Consider: skill gaps, market demand, career progression, learning resources,
networking opportunities, salary expectations.
Prioritize recommendations by impact and feasibility. Cite sources.""",
            user_prompt_template="""Sources:
{sources}

User profile: {profile}
Career goal: {goal}
Current skills: {skills}

Generate prioritized, actionable recommendations with citations.""",
            variables=["sources", "profile", "goal", "skills"],
        ))

        # Extraction
        self.register(PromptTemplate(
            name="extract_information",
            type=PromptType.EXTRACTION,
            system_prompt="""You are an information extraction specialist. Extract specific information
from the provided sources based on the user's request.
Return structured data (JSON format preferred). Include confidence scores.
If information is not found, indicate missing fields.""",
            user_prompt_template="""Sources:
{sources}

Extract the following information:
{extraction_schema}

Return as JSON with confidence scores.""",
            variables=["sources", "extraction_schema"],
        ))

        # Fact Checking
        self.register(PromptTemplate(
            name="fact_check",
            type=PromptType.FACT_CHECKING,
            system_prompt="""You are a fact-checker. Evaluate the accuracy of the given claim
using the provided sources.
Classify as: VERIFIED (multiple credible sources agree), LIKELY (single credible source),
CONFLICTING (sources disagree), UNCERTAIN (insufficient evidence), REJECTED (evidence contradicts).
Provide reasoning and cite specific evidence.""",
            user_prompt_template="""Sources:
{sources}

Claim to verify: {claim}

Provide verdict with reasoning and citations.""",
            variables=["sources", "claim"],
        ))

        # Conversational
        self.register(PromptTemplate(
            name="conversational_rag",
            type=PromptType.CONVERSATIONAL,
            system_prompt="""You are a knowledgeable career advisor having a conversation with a user.
Use the provided context to answer questions naturally.
Reference previous conversation when relevant.
Be helpful, encouraging, and specific.
If you don't know something, say so and offer to research it.""",
            user_prompt_template="""Context:
{context}

Conversation history:
{history}

Current question: {question}

Respond naturally as a career advisor.""",
            variables=["context", "history", "question"],
        ))

        # Job Matching
        self.register(PromptTemplate(
            name="job_match_explanation",
            type=PromptType.ANALYSIS,
            system_prompt="""You are a job matching expert. Explain why a job matches (or doesn't match)
a candidate's profile. Consider: skills match, experience level, location preferences,
salary expectations, company culture, career growth.
Be specific about matching and missing skills.
Provide actionable advice for the candidate.""",
            user_prompt_template="""Job details:
{job_details}

Candidate profile:
{candidate_profile}

Match analysis:
{match_analysis}

Provide a clear explanation of the match with specific examples.""",
            variables=["job_details", "candidate_profile", "match_analysis"],
        ))

        # Resume Feedback
        self.register(PromptTemplate(
            name="resume_feedback",
            type=PromptType.RECOMMENDATION,
            system_prompt="""You are an expert resume reviewer and career coach.
Analyze the resume against the target job/role.
Provide specific, actionable feedback on:
- ATS compatibility
- Content quality and relevance
- Missing keywords/skills
- Formatting and structure
- Quantifiable achievements
- Overall impression
Be constructive and specific. Cite industry standards when applicable.""",
            user_prompt_template="""Resume content:
{resume_content}

Target role: {target_role}
Target job (optional): {job_description}

Provide comprehensive feedback with specific suggestions.""",
            variables=["resume_content", "target_role", "job_description"],
        ))

    def register(self, template: PromptTemplate):
        """Register a prompt template."""
        self._templates[template.name] = template

    def get(self, name: str) -> Optional[PromptTemplate]:
        """Get a prompt template by name."""
        return self._templates.get(name)

    def list_templates(self) -> List[Dict[str, Any]]:
        """List all registered templates."""
        return [
            {
                "name": t.name,
                "type": t.type.value,
                "variables": t.variables,
                "description": t.metadata.get("description", ""),
            }
            for t in self._templates.values()
        ]

    def format_prompt(self, name: str, **kwargs) -> Dict[str, str]:
        """Format a prompt template with variables."""
        template = self.get(name)
        if not template:
            raise ValueError(f"Template not found: {name}")
        return template.format(**kwargs)


# Pre-built context builders for RAG
class ContextBuilder:
    """Build context strings from retrieval results."""

    @staticmethod
    def build_qa_context(
        results: List[Dict[str, Any]],
        max_chars: int = 8000,
        include_metadata: bool = True,
    ) -> str:
        """Build context string for QA prompts."""
        context_parts = []
        current_length = 0

        for i, result in enumerate(results, 1):
            content = result.get("content", "")
            metadata = result.get("metadata", {})
            source_title = result.get("source_title", "Unknown Source")
            source_url = result.get("source_url", "")
            source_type = result.get("source_type", "unknown")

            source_info = f"Source {i}: {source_title}"
            if source_url:
                source_info += f" ({source_url})"
            source_info += f" [Type: {source_type}]"

            chunk = f"[{i}] {source_info}\n{content}"

            if current_length + len(chunk) > max_chars:
                break

            context_parts.append(chunk)
            current_length += len(chunk)

        return "\n\n".join(context_parts)

    @staticmethod
    def build_summary_context(
        results: List[Dict[str, Any]],
        group_by: Optional[str] = None,
    ) -> str:
        """Build context for summarization."""
        if group_by and results:
            # Group by specified metadata field
            groups = {}
            for r in results:
                key = r.get("metadata", {}).get(group_by, "Other")
                if key not in groups:
                    groups[key] = []
                groups[key].append(r)

            parts = []
            for group_name, group_results in groups.items():
                parts.append(f"\n=== {group_name} ===")
                for i, r in enumerate(group_results, 1):
                    parts.append(f"  {i}. {r.get('content', '')[:500]}...")
            return "\n".join(parts)
        else:
            return ContextBuilder.build_qa_context(results)

    @staticmethod
    def build_comparison_context(
        results: Dict[str, List[Dict[str, Any]]],
    ) -> str:
        """Build context for entity comparison."""
        parts = []
        for entity_name, entity_results in results.items():
            parts.append(f"\n=== {entity_name} ===")
            for i, r in enumerate(entity_results[:5], 1):
                content = r.get("content", "")[:300]
                parts.append(f"  {i}. {content}...")
        return "\n".join(parts)

    @staticmethod
    def build_analysis_context(
        results: List[Dict[str, Any]],
        time_field: str = "published_date",
    ) -> str:
        """Build context for trend analysis with temporal ordering."""
        # Sort by date if available
        sorted_results = sorted(
            results,
            key=lambda r: r.get("metadata", {}).get(time_field, ""),
            reverse=True,
        )

        parts = []
        for i, r in enumerate(sorted_results, 1):
            date = r.get("metadata", {}).get(time_field, "Unknown date")
            content = r.get("content", "")[:400]
            parts.append(f"[{i}] ({date}) {content}...")

        return "\n\n".join(parts)


# Response formatters for consistent output
class ResponseFormatter:
    """Format RAG responses consistently."""

    @staticmethod
    def format_qa_response(
        answer: str,
        citations: List[Dict[str, Any]],
        confidence: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Format QA response."""
        return {
            "type": "qa",
            "answer": answer,
            "citations": citations,
            "confidence": confidence,
            "metadata": metadata or {},
        }

    @staticmethod
    def format_summary_response(
        summary: str,
        key_points: List[str],
        sources: List[Dict[str, Any]],
        confidence: float,
    ) -> Dict[str, Any]:
        """Format summarization response."""
        return {
            "type": "summary",
            "summary": summary,
            "key_points": key_points,
            "sources": [{"title": s.get("source_title"), "url": s.get("source_url")} for s in sources],
            "confidence": confidence,
        }

    @staticmethod
    def format_comparison_response(
        comparison: Dict[str, Any],
        confidence: float,
    ) -> Dict[str, Any]:
        """Format comparison response."""
        return {
            "type": "comparison",
            "comparison": comparison,
            "confidence": confidence,
        }

    @staticmethod
    def format_recommendation_response(
        recommendations: List[Dict[str, Any]],
        rationale: str,
        confidence: float,
    ) -> Dict[str, Any]:
        """Format recommendation response."""
        return {
            "type": "recommendation",
            "recommendations": recommendations,
            "rationale": rationale,
            "confidence": confidence,
        }

    @staticmethod
    def format_error_response(
        error: str,
        error_type: str = "general",
    ) -> Dict[str, Any]:
        """Format error response."""
        return {
            "type": "error",
            "error": error,
            "error_type": error_type,
        }


# Few-shot examples for better prompt performance
FEW_SHOT_EXAMPLES = {
    "qa": [
        {
            "question": "What is the average salary for a Python developer in 2024?",
            "context": "[1] TechSalaries 2024 Report: Python developers earn $120k-$160k average... [2] StackOverflow Survey: Median Python salary $130k...",
            "answer": "Based on the sources, Python developers earn an average of $120k-$160k in 2024 [1], with a median of $130k according to StackOverflow [2].",
        }
    ],
    "summarization": [
        {
            "sources": "[1] Python demand growing 25% YoY... [2] AI/ML roles up 40%... [3] Remote work still 40% of tech jobs...",
            "summary": "Key trends in 2024 tech job market: Python demand growing 25% year-over-year [1], AI/ML roles surging 40% [2], and remote work remaining at 40% of tech positions [3].",
        }
    ],
    "comparison": [
        {
            "entities": "Senior Python Developer vs ML Engineer",
            "context": "[1] Senior Python: $130k-180k, skills: Python, FastAPI, PostgreSQL... [2] ML Engineer: $140k-200k, skills: Python, PyTorch, MLOps...",
            "comparison": "Both roles require strong Python skills. ML Engineer pays $10k-20k more but requires ML frameworks (PyTorch/TensorFlow) and MLOps experience [2]. Senior Python focuses on web/backend with FastAPI and databases [1].",
        }
    ],
}


def get_few_shot_examples(task_type: str) -> List[Dict[str, str]]:
    """Get few-shot examples for a task type."""
    return FEW_SHOT_EXAMPLES.get(task_type, [])