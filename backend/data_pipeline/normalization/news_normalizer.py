import logging
import re
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime

from backend.data_pipeline.collectors.base_collector import RawDataRecord

logger = logging.getLogger(__name__)


@dataclass
class NormalizedNews:
    """Normalized news article data ready for database storage."""
    title: str
    summary: Optional[str]
    content: Optional[str]
    source: str
    source_url: str
    source_article_id: str
    author: Optional[str]
    published_date: Optional[datetime]
    retrieved_date: datetime
    topics: List[str]
    companies_mentioned: List[str]
    technologies_mentioned: List[str]
    sentiment: Optional[str]
    language: str
    quality_score: float
    raw_record: Optional[RawDataRecord] = None


TOPIC_KEYWORDS = {
    "ai_ml": ["artificial intelligence", "machine learning", "deep learning", "llm", "generative ai", "neural network", "transformer"],
    "cloud": ["cloud computing", "aws", "azure", "gcp", "kubernetes", "docker", "serverless", "cloud native"],
    "cybersecurity": ["cybersecurity", "security breach", "data breach", "ransomware", "vulnerability", "zero trust"],
    "remote_work": ["remote work", "work from home", "hybrid work", "digital nomad", "distributed team"],
    "hiring": ["hiring", "recruitment", "job market", "layoffs", "talent shortage", "skills gap"],
    "salary": ["salary", "compensation", "pay transparency", "wage growth", "benefits"],
    "startup": ["startup", "venture capital", "funding", "ipo", "acquisition", "unicorn"],
    "big_tech": ["google", "microsoft", "amazon", "apple", "meta", "netflix", "tesla"],
    "web3": ["blockchain", "cryptocurrency", "web3", "defi", "nft", "smart contract"],
    "data": ["data science", "analytics", "big data", "data engineering", "etl"],
    "devops": ["devops", "ci/cd", "infrastructure", "observability", "platform engineering"],
    "frontend": ["frontend", "react", "vue", "angular", "web development", "typescript"],
    "backend": ["backend", "api", "microservices", "database", "distributed systems"],
    "mobile": ["mobile", "ios", "android", "flutter", "react native", "swift", "kotlin"],
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
]

COMPANY_KEYWORDS = [
    "google", "microsoft", "amazon", "apple", "meta", "facebook", "netflix", "tesla",
    "openai", "anthropic", "nvidia", "amd", "intel", "salesforce", "oracle", "ibm",
    "uber", "airbnb", "stripe", "shopify", "spotify", "slack", "zoom", "atlassian",
    "github", "gitlab", "databricks", "snowflake", "confluent", "hashicorp", "vercel",
]


def extract_topics(text: str) -> List[str]:
    """Extract topics from text based on keywords."""
    text_lower = text.lower()
    found = []
    for topic, keywords in TOPIC_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                found.append(topic)
                break
    return found


def extract_companies(text: str) -> List[str]:
    """Extract mentioned companies from text."""
    text_lower = text.lower()
    found = []
    for company in COMPANY_KEYWORDS:
        if re.search(rf"\b{re.escape(company)}\b", text_lower):
            found.append(company.title())
    return list(set(found))


def extract_technologies(text: str) -> List[str]:
    """Extract mentioned technologies from text."""
    text_lower = text.lower()
    found = []
    for tech in TECHNOLOGY_KEYWORDS:
        if re.search(rf"\b{re.escape(tech)}\b", text_lower):
            found.append(tech)
    return list(set(found))


def detect_sentiment(text: str) -> Optional[str]:
    """Simple sentiment detection based on keywords."""
    text_lower = text.lower()
    
    positive_words = ["growth", "success", "innovation", "breakthrough", "record", "surge", "boom", "optimistic", "bullish", "expanding", "hiring", "investment", "funding", "launch"]
    negative_words = ["layoff", "cut", "decline", "crisis", "recession", "downturn", "pessimistic", "bearish", "bankruptcy", "lawsuit", "scandal", "breach", "failure", "shutdown"]
    
    pos_count = sum(1 for w in positive_words if w in text_lower)
    neg_count = sum(1 for w in negative_words if w in text_lower)
    
    if pos_count > neg_count:
        return "positive"
    elif neg_count > pos_count:
        return "negative"
    return "neutral"


class NewsNormalizer:
    """Normalize raw news data from various sources into standard format."""

    def __init__(self):
        self.name = "news_normalizer"

    def normalize(self, raw_record: RawDataRecord) -> NormalizedNews:
        """Normalize a single raw news record."""
        payload = raw_record.raw_payload
        logger.debug(f"Normalizing news: {payload.get('title')[:50]}...")

        title = payload.get("title", "").strip()
        summary = payload.get("summary", "").strip() if payload.get("summary") else None
        content = payload.get("content", "").strip() if payload.get("content") else None
        
        full_text = " ".join(filter(None, [title, summary, content]))
        
        topics = payload.get("topics") or extract_topics(full_text)
        companies = payload.get("companies_mentioned") or extract_companies(full_text)
        technologies = payload.get("technologies_mentioned") or extract_technologies(full_text)
        sentiment = payload.get("sentiment") or detect_sentiment(full_text)
        
        published_date = payload.get("published_date")
        if isinstance(published_date, str):
            try:
                published_date = datetime.fromisoformat(published_date.replace("Z", "+00:00"))
            except Exception:
                published_date = None
        
        retrieved_date = payload.get("retrieved_date")
        if isinstance(retrieved_date, str):
            try:
                retrieved_date = datetime.fromisoformat(retrieved_date.replace("Z", "+00:00"))
            except Exception:
                retrieved_date = datetime.utcnow()
        elif not retrieved_date:
            retrieved_date = datetime.utcnow()

        author = payload.get("author", "").strip() if payload.get("author") else None
        language = payload.get("language", "en")

        return NormalizedNews(
            title=title,
            summary=summary,
            content=content,
            source=raw_record.source_name,
            source_url=payload.get("source_url", ""),
            source_article_id=payload.get("source_article_id", raw_record.external_id),
            author=author,
            published_date=published_date,
            retrieved_date=retrieved_date,
            topics=topics,
            companies_mentioned=companies,
            technologies_mentioned=technologies,
            sentiment=sentiment,
            language=language,
            quality_score=payload.get("quality_score", 0.0),
            raw_record=raw_record,
        )

    def normalize_batch(self, raw_records: List[RawDataRecord]) -> List[NormalizedNews]:
        """Normalize multiple raw news records."""
        return [self.normalize(record) for record in raw_records]