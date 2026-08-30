from datetime import datetime
from typing import Optional, List, Dict, Any, Set
from dataclasses import dataclass, field
from enum import Enum as PyEnum
from uuid import uuid4


class ResearchType(str, PyEnum):
    """Types of research."""
    JOB_MARKET = "job_market"
    COMPANY = "company"
    TECHNOLOGY = "technology"
    CAREER_PATH = "career_path"
    SKILL_ANALYSIS = "skill_analysis"
    SALARY = "salary"
    INTERVIEW_PREP = "interview_prep"
    GENERAL = "general"


class ResearchSourceType(str, PyEnum):
    """Types of sources."""
    WEB = "web"
    NEWS = "news"
    ACADEMIC = "academic"
    COMPANY = "company"
    JOB_BOARD = "job_board"
    SOCIAL = "social"
    GOVERNMENT = "government"
    INTERNAL = "internal"
    OTHER = "other"


class ResearchEvidenceType(str, PyEnum):
    """Types of evidence."""
    DIRECT_QUOTE = "direct_quote"
    STATISTIC = "statistic"
    EXPERT_OPINION = "expert_opinion"
    CASE_STUDY = "case_study"
    SURVEY_RESULT = "survey_result"
    REPORT = "report"
    OTHER = "other"


@dataclass
class SourceMetadata:
    """Metadata for a research source."""
    url: str
    title: str
    source_type: ResearchSourceType
    domain: Optional[str] = None
    author: Optional[str] = None
    published_date: Optional[datetime] = None
    retrieved_date: datetime = field(default_factory=datetime.utcnow)
    credibility_score: float = 0.5
    relevance_score: float = 0.5
    content_hash: Optional[str] = None
    word_count: int = 0
    language: str = "en"
    tags: List[str] = field(default_factory=list)
    custom_metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "title": self.title,
            "source_type": self.source_type.value,
            "domain": self.domain,
            "author": self.author,
            "published_date": self.published_date.isoformat() if self.published_date else None,
            "retrieved_date": self.retrieved_date.isoformat(),
            "credibility_score": self.credibility_score,
            "relevance_score": self.relevance_score,
            "content_hash": self.content_hash,
            "word_count": self.word_count,
            "language": self.language,
            "tags": self.tags,
            "custom_metadata": self.custom_metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SourceMetadata":
        metadata = cls(
            url=data["url"],
            title=data["title"],
            source_type=ResearchSourceType(data["source_type"]),
            domain=data.get("domain"),
            author=data.get("author"),
            published_date=datetime.fromisoformat(data["published_date"]) if data.get("published_date") else None,
            retrieved_date=datetime.fromisoformat(data["retrieved_date"]) if data.get("retrieved_date") else datetime.utcnow(),
            credibility_score=data.get("credibility_score", 0.5),
            relevance_score=data.get("relevance_score", 0.5),
            content_hash=data.get("content_hash"),
            word_count=data.get("word_count", 0),
            language=data.get("language", "en"),
            tags=data.get("tags", []),
            custom_metadata=data.get("custom_metadata", {}),
        )
        return metadata


@dataclass
class ResearchClaim:
    """A claim extracted from sources."""
    id: str = field(default_factory=lambda: str(uuid4()))
    text: str = ""
    claim_type: Optional[str] = None  # fact, statistic, opinion, prediction
    source_ids: List[str] = field(default_factory=list)
    confidence: float = 0.0
    status: str = "extracted"  # extracted, verified, conflicting, rejected
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "text": self.text,
            "claim_type": self.claim_type,
            "source_ids": self.source_ids,
            "confidence": self.confidence,
            "status": self.status,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class ResearchEvidence:
    """Evidence supporting or refuting a claim."""
    id: str = field(default_factory=lambda: str(uuid4()))
    claim_id: str = ""
    source_id: str = ""
    text: str = ""
    evidence_type: str = "direct_quote"  # direct_quote, statistic, expert_opinion, case_study, survey_result, report
    supports_claim: bool = True
    relevance_score: float = 0.0
    confidence_score: float = 0.0
    citation_context: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "claim_id": self.claim_id,
            "source_id": self.source_id,
            "text": self.text,
            "evidence_type": self.evidence_type,
            "supports_claim": self.supports_claim,
            "relevance_score": self.relevance_score,
            "confidence_score": self.confidence_score,
            "citation_context": self.citation_context,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class ResearchTask:
    """A research task."""
    id: str = field(default_factory=lambda: str(uuid4()))
    description: str = ""
    agent_type: str = ""  # web, news, job_market, company, academic
    query: str = ""
    priority: int = 1
    status: str = "pending"  # pending, running, completed, failed
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    sources: List[SourceMetadata] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "agent_type": self.agent_type,
            "query": self.query,
            "priority": self.priority,
            "status": self.status,
            "result": self.result,
            "error": self.error,
            "sources": [s.to_dict() for s in self.sources],
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


@dataclass
class ResearchPlan:
    """A research plan with tasks."""
    id: str = field(default_factory=lambda: str(uuid4()))
    research_id: int = 0
    query: str = ""
    research_type: ResearchType = ResearchType.GENERAL
    tasks: List[ResearchTask] = field(default_factory=list)
    max_sources: int = 10
    timeout_seconds: int = 300
    target_role: Optional[str] = None
    target_company: Optional[str] = None
    target_location: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "research_id": self.research_id,
            "query": self.query,
            "research_type": self.research_type.value,
            "tasks": [t.to_dict() for t in self.tasks],
            "max_sources": self.max_sources,
            "timeout_seconds": self.timeout_seconds,
            "target_role": self.target_role,
            "target_company": self.target_company,
            "target_location": self.target_location,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ResearchPlan":
        plan = cls(
            id=data["id"],
            research_id=data["research_id"],
            query=data["query"],
            research_type=ResearchType(data["research_type"]),
            max_sources=data.get("max_sources", 10),
            timeout_seconds=data.get("timeout_seconds", 300),
            target_role=data.get("target_role"),
            target_company=data.get("target_company"),
            target_location=data.get("target_location"),
        )
        if "tasks" in data:
            for t in data["tasks"]:
                task = ResearchTask(
                    id=t["id"],
                    description=t["description"],
                    agent_type=t["agent_type"],
                    query=t["query"],
                    priority=t.get("priority", 1),
                    status=t.get("status", "pending"),
                    result=t.get("result"),
                    error=t.get("error"),
                )
                if "created_at" in t:
                    task.created_at = datetime.fromisoformat(t["created_at"])
                if "started_at" in t and t["started_at"]:
                    task.started_at = datetime.fromisoformat(t["started_at"])
                if "completed_at" in t and t["completed_at"]:
                    task.completed_at = datetime.fromisoformat(t["completed_at"])
                if "sources" in t:
                    task.sources = [SourceMetadata.from_dict(s) for s in t["sources"]]
                plan.tasks.append(task)
        return plan


@dataclass
class ResearchResult:
    """Complete research result."""
    research_id: int
    query: str
    research_type: ResearchType
    state: str = "completed"
    plan: Optional[ResearchPlan] = None
    sources: List[SourceMetadata] = field(default_factory=list)
    claims: List[ResearchClaim] = field(default_factory=list)
    evidence: List[ResearchEvidence] = field(default_factory=list)
    verification_results: List[Dict[str, Any]] = field(default_factory=list)
    analysis: Optional[Dict[str, Any]] = None
    synthesis: Optional[Dict[str, Any]] = None
    report: Optional[Dict[str, Any]] = None
    confidence_score: float = 0.0
    completed_at: datetime = field(default_factory=datetime.utcnow)
    execution_time_seconds: float = 0.0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "research_id": self.research_id,
            "query": self.query,
            "research_type": self.research_type.value,
            "state": self.state,
            "plan": self.plan.to_dict() if self.plan else None,
            "sources": [s.to_dict() for s in self.sources],
            "claims": [c.to_dict() for c in self.claims],
            "evidence": [e.to_dict() for e in self.evidence],
            "verification_results": self.verification_results,
            "analysis": self.analysis,
            "synthesis": self.synthesis,
            "report": self.report,
            "confidence_score": self.confidence_score,
            "completed_at": self.completed_at.isoformat(),
            "execution_time_seconds": self.execution_time_seconds,
            "errors": self.errors,
            "warnings": self.warnings,
        }