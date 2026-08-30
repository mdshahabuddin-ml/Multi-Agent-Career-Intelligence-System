import logging
import re
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime

from backend.data_pipeline.collectors.base_collector import RawDataRecord

logger = logging.getLogger(__name__)


@dataclass
class NormalizedResearch:
    """Normalized research document data ready for database storage."""
    title: str
    authors: List[str]
    abstract: Optional[str]
    content: Optional[str]
    source: str
    source_url: str
    source_document_id: str
    publication_date: Optional[datetime]
    retrieved_date: datetime
    research_type: str
    topics: List[str]
    keywords: List[str]
    doi: Optional[str]
    venue: Optional[str]
    citation_count: Optional[int]
    quality_score: float
    raw_record: Optional[RawDataRecord] = None


RESEARCH_TYPE_KEYWORDS = {
    "academic_paper": ["arxiv", "paper", "journal", "conference", "proceedings", "preprint"],
    "industry_report": ["report", "whitepaper", "market research", "industry analysis", "gartner", "forrester", "idc"],
    "technical_blog": ["blog", "engineering blog", "tech blog", "medium.com", "dev.to", "hashicorp", "netflix tech blog"],
    "documentation": ["documentation", "docs", "api reference", "user guide", "tutorial"],
    "case_study": ["case study", "customer story", "success story", "implementation"],
    "benchmark": ["benchmark", "performance comparison", "evaluation", "leaderboard"],
}

TECHNOLOGY_KEYWORDS = [
    "python", "javascript", "typescript", "java", "c++", "c#", "go", "rust", "ruby", "php",
    "react", "vue", "angular", "svelte", "next.js", "nuxt", "django", "flask", "fastapi",
    "spring", "express", "node.js", "deno", "bun", "rails", "laravel", ".net",
    "postgresql", "mysql", "mongodb", "redis", "elasticsearch", "sqlite", "dynamodb",
    "docker", "kubernetes", "aws", "gcp", "azure", "terraform", "ansible", "helm",
    "git", "github", "gitlab", "ci/cd", "jenkins", "github actions", "circleci",
    "machine learning", "deep learning", "tensorflow", "pytorch", "scikit-learn",
    "pandas", "numpy", "sql", "nosql", "graphql", "rest", "grpc",
    "microservices", "serverless", "event-driven", "kafka", "rabbitmq",
    "linux", "bash", "vim", "vscode", "intellij",
    "agile", "scrum", "kanban", "jira", "confluence",
    "html", "css", "sass", "tailwind", "bootstrap",
    "testing", "jest", "pytest", "cypress", "playwright",
    "llm", "transformer", "bert", "gpt", "llama", "rag", "vector database", "embedding",
]


def classify_research_type(text: str, source_url: str) -> str:
    """Classify research document type based on content and source."""
    text_lower = text.lower()
    url_lower = source_url.lower()
    
    for rtype, keywords in RESEARCH_TYPE_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower or kw in url_lower:
                return rtype
    return "technical_blog"


def extract_topics(text: str) -> List[str]:
    """Extract research topics from text."""
    text_lower = text.lower()
    
    topic_keywords = {
        "ai_ml": ["artificial intelligence", "machine learning", "deep learning", "llm", "generative ai", "neural network", "transformer", "bert", "gpt", "llama"],
        "nlp": ["natural language processing", "nlp", "language model", "text generation", "translation", "sentiment analysis"],
        "cv": ["computer vision", "image recognition", "object detection", "segmentation", "classification"],
        "rl": ["reinforcement learning", "rl", "policy gradient", "q-learning", "actor-critic"],
        "data_engineering": ["data engineering", "etl", "data pipeline", "data warehouse", "lakehouse", "streaming"],
        "mlops": ["mlops", "model deployment", "model serving", "feature store", "experiment tracking", "model monitoring"],
        "distributed_systems": ["distributed systems", "consensus", "raft", "paxos", "microservices", "service mesh"],
        "cloud_native": ["cloud native", "kubernetes", "container", "serverless", "service mesh", "istio"],
        "security": ["security", "cryptography", "authentication", "authorization", "zero trust", "vulnerability"],
        "performance": ["performance", "optimization", "latency", "throughput", "benchmark", "profiling"],
        "architecture": ["architecture", "system design", "design pattern", "domain driven design", "event sourcing"],
        "developer_experience": ["developer experience", "dx", "cli", "api design", "documentation", "tooling"],
    }
    
    found = []
    for topic, keywords in topic_keywords.items():
        for kw in keywords:
            if kw in text_lower:
                found.append(topic)
                break
    return found


def extract_technologies(text: str) -> List[str]:
    """Extract technologies from text."""
    text_lower = text.lower()
    found = []
    for tech in TECHNOLOGY_KEYWORDS:
        if re.search(rf"\b{re.escape(tech)}\b", text_lower):
            found.append(tech)
    return list(set(found))


def extract_authors(payload: Dict[str, Any]) -> List[str]:
    """Extract authors from various payload formats."""
    authors = payload.get("authors")
    if authors:
        if isinstance(authors, str):
            return [a.strip() for a in authors.split(",")]
        elif isinstance(authors, list):
            return [str(a).strip() for a in authors]
    
    # Try single author field
    author = payload.get("author")
    if author:
        return [author.strip()]
    
    return []


class ResearchNormalizer:
    """Normalize raw research data from various sources into standard format."""

    def __init__(self):
        self.name = "research_normalizer"

    def normalize(self, raw_record: RawDataRecord) -> NormalizedResearch:
        """Normalize a single raw research record."""
        payload = raw_record.raw_payload
        logger.debug(f"Normalizing research: {payload.get('title')[:50]}...")

        title = payload.get("title", "").strip()
        abstract = payload.get("abstract", "").strip() if payload.get("abstract") else None
        content = payload.get("content", "").strip() if payload.get("content") else None
        
        full_text = " ".join(filter(None, [title, abstract, content]))
        
        authors = payload.get("authors") or extract_authors(payload)
        research_type = payload.get("research_type") or classify_research_type(full_text, payload.get("source_url", ""))
        topics = payload.get("topics") or extract_topics(full_text)
        keywords = payload.get("keywords") or []
        technologies = payload.get("technologies_mentioned") or extract_technologies(full_text)
        
        if not keywords and technologies:
            keywords = technologies[:10]
        
        publication_date = payload.get("publication_date") or payload.get("published_date")
        if isinstance(publication_date, str):
            try:
                publication_date = datetime.fromisoformat(publication_date.replace("Z", "+00:00"))
            except Exception:
                publication_date = None
        
        retrieved_date = payload.get("retrieved_date")
        if isinstance(retrieved_date, str):
            try:
                retrieved_date = datetime.fromisoformat(retrieved_date.replace("Z", "+00:00"))
            except Exception:
                retrieved_date = datetime.utcnow()
        elif not retrieved_date:
            retrieved_date = datetime.utcnow()
        
        doi = payload.get("doi")
        venue = payload.get("venue") or payload.get("journal") or payload.get("conference")
        
        citation_count = payload.get("citation_count")
        if isinstance(citation_count, str):
            try:
                citation_count = int(citation_count)
            except Exception:
                citation_count = None

        return NormalizedResearch(
            title=title,
            authors=authors,
            abstract=abstract,
            content=content,
            source=raw_record.source_name,
            source_url=payload.get("source_url", ""),
            source_document_id=payload.get("source_document_id", raw_record.external_id),
            publication_date=publication_date,
            retrieved_date=retrieved_date,
            research_type=research_type,
            topics=topics,
            keywords=keywords,
            doi=doi,
            venue=venue,
            citation_count=citation_count,
            quality_score=payload.get("quality_score", 0.0),
            raw_record=raw_record,
        )

    def normalize_batch(self, raw_records: List[RawDataRecord]) -> List[NormalizedResearch]:
        """Normalize multiple raw research records."""
        return [self.normalize(record) for record in raw_records]