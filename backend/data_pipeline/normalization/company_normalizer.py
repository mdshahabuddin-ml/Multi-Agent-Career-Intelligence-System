import logging
import re
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime

from backend.data_pipeline.collectors.base_collector import RawDataRecord

logger = logging.getLogger(__name__)


@dataclass
class NormalizedCompany:
    """Normalized company data ready for database storage."""
    name: str
    normalized_name: str
    domain: Optional[str]
    description: Optional[str]
    industry: Optional[str]
    company_size: Optional[str]
    headquarters: Optional[str]
    founded_year: Optional[int]
    website: Optional[str]
    linkedin_url: Optional[str]
    logo_url: Optional[str]
    tech_stack: List[str]
    culture_tags: List[str]
    benefits: List[str]
    glassdoor_rating: Optional[float]
    glassdoor_reviews_count: Optional[int]
    source: str
    source_url: str
    source_company_id: str
    quality_score: float
    raw_record: Optional[RawDataRecord] = None


INDUSTRY_NORMALIZATION = {
    "software": "Technology",
    "tech": "Technology",
    "technology": "Technology",
    "it": "Technology",
    "saas": "Technology",
    "fintech": "Financial Technology",
    "finance": "Finance",
    "banking": "Finance",
    "healthcare": "Healthcare",
    "medical": "Healthcare",
    "biotech": "Biotechnology",
    "pharma": "Pharmaceuticals",
    "education": "Education",
    "edtech": "Education Technology",
    "retail": "Retail",
    "ecommerce": "E-commerce",
    "manufacturing": "Manufacturing",
    "automotive": "Automotive",
    "energy": "Energy",
    "consulting": "Consulting",
    "media": "Media",
    "entertainment": "Entertainment",
    "gaming": "Gaming",
    "telecommunications": "Telecommunications",
    "real estate": "Real Estate",
    "construction": "Construction",
    "transportation": "Transportation",
    "logistics": "Logistics",
}

COMPANY_SIZE_NORMALIZATION = {
    "1-10": "1-10",
    "11-50": "11-50",
    "51-200": "51-200",
    "201-500": "201-500",
    "501-1000": "501-1000",
    "1001-5000": "1001-5000",
    "5001-10000": "5001-10000",
    "10000+": "10000+",
    "startup": "1-50",
    "small": "11-200",
    "medium": "201-1000",
    "large": "1001-10000",
    "enterprise": "10000+",
}

TECH_STACK_KEYWORDS = [
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


def normalize_industry(industry: Optional[str]) -> Optional[str]:
    """Normalize industry to standard categories."""
    if not industry:
        return None
    industry_lower = industry.lower().strip()
    for key, val in INDUSTRY_NORMALIZATION.items():
        if key in industry_lower:
            return val
    return industry


def normalize_company_size(size: Optional[str]) -> Optional[str]:
    """Normalize company size to standard buckets."""
    if not size:
        return None
    size_lower = size.lower().strip()
    for key, val in COMPANY_SIZE_NORMALIZATION.items():
        if key in size_lower:
            return val
    return size


def extract_tech_stack(text: str) -> List[str]:
    """Extract technology stack from text."""
    text_lower = text.lower()
    found = []
    for tech in TECH_STACK_KEYWORDS:
        if re.search(rf"\b{re.escape(tech)}\b", text_lower):
            found.append(tech)
    return found


def extract_domain_from_website(website: str) -> Optional[str]:
    """Extract domain from website URL."""
    if not website:
        return None
    import urllib.parse
    try:
        parsed = urllib.parse.urlparse(website if website.startswith("http") else f"https://{website}")
        domain = parsed.netloc.replace("www.", "")
        return domain if domain else None
    except Exception:
        return None


class CompanyNormalizer:
    """Normalize raw company data from various sources into standard format."""

    def __init__(self):
        self.name = "company_normalizer"

    def normalize(self, raw_record: RawDataRecord) -> NormalizedCompany:
        """Normalize a single raw company record."""
        payload = raw_record.raw_payload
        logger.debug(f"Normalizing company: {payload.get('name')}")

        # Extract and normalize fields
        name = payload.get("name", "").strip()
        normalized_name = name.lower()
        domain = payload.get("domain") or extract_domain_from_website(payload.get("website", ""))
        
        description = payload.get("description", "").strip() if payload.get("description") else None
        industry = normalize_industry(payload.get("industry"))
        company_size = normalize_company_size(payload.get("company_size"))
        headquarters = payload.get("headquarters", "").strip() if payload.get("headquarters") else None
        
        founded_year = payload.get("founded_year")
        if isinstance(founded_year, str):
            try:
                founded_year = int(founded_year)
            except Exception:
                founded_year = None
        
        website = payload.get("website")
        linkedin_url = payload.get("linkedin_url")
        logo_url = payload.get("logo_url")
        
        tech_stack = payload.get("tech_stack") or []
        if not tech_stack:
            tech_stack = extract_tech_stack(
                (payload.get("description") or "") + " " + " ".join(payload.get("culture_tags") or [])
            )
        
        culture_tags = payload.get("culture_tags") or []
        benefits = payload.get("benefits") or []
        
        glassdoor_rating = payload.get("glassdoor_rating")
        if isinstance(glassdoor_rating, str):
            try:
                glassdoor_rating = float(glassdoor_rating)
            except Exception:
                glassdoor_rating = None
        
        glassdoor_reviews_count = payload.get("glassdoor_reviews_count")
        if isinstance(glassdoor_reviews_count, str):
            try:
                glassdoor_reviews_count = int(glassdoor_reviews_count)
            except Exception:
                glassdoor_reviews_count = None

        return NormalizedCompany(
            name=name,
            normalized_name=normalized_name,
            domain=domain,
            description=description,
            industry=industry,
            company_size=company_size,
            headquarters=headquarters,
            founded_year=founded_year,
            website=website,
            linkedin_url=linkedin_url,
            logo_url=logo_url,
            tech_stack=tech_stack,
            culture_tags=culture_tags,
            benefits=benefits,
            glassdoor_rating=glassdoor_rating,
            glassdoor_reviews_count=glassdoor_reviews_count,
            source=raw_record.source_name,
            source_url=payload.get("source_url", ""),
            source_company_id=payload.get("source_company_id", raw_record.external_id),
            quality_score=payload.get("quality_score", 0.0),
            raw_record=raw_record,
        )

    def normalize_batch(self, raw_records: List[RawDataRecord]) -> List[NormalizedCompany]:
        """Normalize multiple raw company records."""
        return [self.normalize(record) for record in raw_records]