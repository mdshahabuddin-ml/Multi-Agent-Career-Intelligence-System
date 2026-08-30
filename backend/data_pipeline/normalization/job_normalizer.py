import logging
import re
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime

from backend.data_pipeline.collectors.base_collector import RawDataRecord

logger = logging.getLogger(__name__)


@dataclass
class NormalizedJob:
    """Normalized job data ready for database storage."""
    title: str
    company_name: str
    company_domain: Optional[str]
    location: str
    normalized_location: str
    is_remote: bool
    remote_type: Optional[str]
    description: str
    requirements: Optional[str]
    responsibilities: Optional[str]
    salary_min: Optional[int]
    salary_max: Optional[int]
    salary_currency: str
    salary_period: Optional[str]
    salary_yearly_min: Optional[int]
    salary_yearly_max: Optional[int]
    experience_level: Optional[str]
    employment_type: Optional[str]
    source: str
    source_url: str
    source_job_id: str
    posted_date: Optional[datetime]
    expires_date: Optional[datetime]
    application_url: Optional[str]
    application_email: Optional[str]
    skills: List[str]
    keywords: List[str]
    quality_score: float
    raw_record: Optional[RawDataRecord] = None


SALARY_PERIODS = {
    "hourly": 2080,
    "monthly": 12,
    "yearly": 1,
    "annually": 1,
    "weekly": 52,
    "daily": 260,
}

EXPERIENCE_LEVELS = {
    "intern": 0,
    "entry": 1,
    "junior": 1,
    "mid": 3,
    "senior": 5,
    "lead": 7,
    "principal": 10,
    "staff": 8,
    "director": 10,
}

EMPLOYMENT_TYPES = {
    "full_time": "full_time",
    "fulltime": "full_time",
    "part_time": "part_time",
    "parttime": "part_time",
    "contract": "contract",
    "contractor": "contract",
    "freelance": "freelance",
    "internship": "internship",
    "temporary": "temporary",
}

REMOTE_TYPES = {
    "remote": "fully_remote",
    "fully remote": "fully_remote",
    "100% remote": "fully_remote",
    "hybrid": "hybrid",
    "partial remote": "hybrid",
    "flexible": "flexible",
    "on-site": "on_site",
    "onsite": "on_site",
    "office": "on_site",
}


def normalize_salary(
    salary_min: Optional[int],
    salary_max: Optional[int],
    currency: str,
    period: Optional[str],
) -> tuple[Optional[int], Optional[int]]:
    """Convert salary to yearly USD equivalent."""
    if not salary_min and not salary_max:
        return None, None

    period = (period or "yearly").lower()
    multiplier = SALARY_PERIODS.get(period, 1)

    currency_rates = {"usd": 1.0, "eur": 1.1, "gbp": 1.25, "cad": 0.75, "aud": 0.65}
    rate = currency_rates.get(currency.lower(), 1.0)

    yearly_min = None
    yearly_max = None

    if salary_min:
        yearly_min = int(salary_min * multiplier * rate)
    if salary_max:
        yearly_max = int(salary_max * multiplier * rate)

    return yearly_min, yearly_max


def normalize_experience_level(level: Optional[str]) -> Optional[str]:
    """Normalize experience level to standard values."""
    if not level:
        return None
    level = level.lower().strip()
    for key, years in EXPERIENCE_LEVELS.items():
        if key in level:
            return key
    match = re.search(r"(\d+)\s*[\+\-]", level)
    if match:
        years = int(match.group(1))
        for key, req_years in EXPERIENCE_LEVELS.items():
            if years <= req_years:
                return key
    return "mid"


def normalize_employment_type(emp_type: Optional[str]) -> Optional[str]:
    """Normalize employment type."""
    if not emp_type:
        return None
    emp_type = emp_type.lower().strip()
    for key, val in EMPLOYMENT_TYPES.items():
        if key in emp_type:
            return val
    return "full_time"


def normalize_remote_type(remote_type: Optional[str], is_remote: bool) -> Optional[str]:
    """Normalize remote work type."""
    if not is_remote:
        return "on_site"
    if not remote_type:
        return "fully_remote"
    remote_type = remote_type.lower().strip()
    for key, val in REMOTE_TYPES.items():
        if key in remote_type:
            return val
    return "fully_remote"


def normalize_location(location: str) -> str:
    """Normalize location string."""
    if not location:
        return "Unknown"
    location = re.sub(r"\s+", " ", location.strip())
    replacements = {
        r"\bNY\b": "New York",
        r"\bCA\b": "California",
        r"\bSF\b": "San Francisco",
        r"\bLA\b": "Los Angeles",
        r"\bDC\b": "Washington DC",
        r"\bTX\b": "Texas",
        r"\bWA\b": "Washington",
        r"\bMA\b": "Massachusetts",
    }
    for pattern, replacement in replacements.items():
        location = re.sub(pattern, replacement, location, flags=re.IGNORECASE)
    return location


TECH_SKILLS = [
    "python", "javascript", "typescript", "java", "c++", "c#", "go", "rust",
    "react", "vue", "angular", "svelte", "next.js", "nuxt", "django", "flask",
    "fastapi", "spring", "express", "node.js", "deno", "bun",
    "postgresql", "mysql", "mongodb", "redis", "elasticsearch", "sqlite",
    "docker", "kubernetes", "aws", "gcp", "azure", "terraform", "ansible",
    "git", "github", "gitlab", "ci/cd", "jenkins", "github actions",
    "machine learning", "deep learning", "tensorflow", "pytorch", "scikit-learn",
    "pandas", "numpy", "sql", "nosql", "graphql", "rest", "grpc",
    "microservices", "serverless", "event-driven", "kafka", "rabbitmq",
    "linux", "bash", "vim", "vscode", "intellij",
    "agile", "scrum", "kanban", "jira", "confluence",
    "html", "css", "sass", "tailwind", "bootstrap",
    "testing", "jest", "pytest", "cypress", "playwright",
]


def extract_skills_from_text(text: str) -> List[str]:
    """Extract skill keywords from job text."""
    text_lower = text.lower()
    found = []
    for skill in TECH_SKILLS:
        if re.search(rf"\b{re.escape(skill)}\b", text_lower):
            found.append(skill)
    return found


def extract_company_domain(company_name: str, source_url: str) -> Optional[str]:
    """Extract company domain from name or URL."""
    import urllib.parse
    try:
        parsed = urllib.parse.urlparse(source_url)
        domain = parsed.netloc.replace("www.", "")
        return domain
    except Exception:
        pass

    name = re.sub(r"[^\w\s]", "", company_name.lower())
    name = re.sub(r"\s+", "", name)
    return f"{name}.com" if name else None


class JobNormalizer:
    """Normalize raw job data from various sources into standard format."""

    def __init__(self):
        self.name = "job_normalizer"

    def normalize(self, raw_record: RawDataRecord) -> NormalizedJob:
        """Normalize a single raw job record."""
        payload = raw_record.raw_payload
        logger.debug(f"Normalizing job: {payload.get('title')} at {payload.get('company')}")

        yearly_min, yearly_max = normalize_salary(
            payload.get("salary_min"),
            payload.get("salary_max"),
            payload.get("salary_currency", "USD"),
            payload.get("salary_period"),
        )

        normalized_location = normalize_location(payload.get("location", ""))
        remote_type = normalize_remote_type(payload.get("remote_type"), payload.get("is_remote", False))

        skills = payload.get("skills") or []
        if not skills:
            skills = extract_skills_from_text(
                (payload.get("description") or "") + " " + (payload.get("requirements") or "")
            )

        keywords = payload.get("keywords") or []
        company_domain = extract_company_domain(payload.get("company", ""), payload.get("source_url", ""))

        posted_date = payload.get("posted_date")
        if isinstance(posted_date, str):
            try:
                posted_date = datetime.fromisoformat(posted_date.replace("Z", "+00:00"))
            except Exception:
                posted_date = None

        expires_date = payload.get("expires_date")
        if isinstance(expires_date, str):
            try:
                expires_date = datetime.fromisoformat(expires_date.replace("Z", "+00:00"))
            except Exception:
                expires_date = None

        return NormalizedJob(
            title=payload.get("title", "").strip(),
            company_name=payload.get("company", "").strip(),
            company_domain=company_domain,
            location=payload.get("location", "").strip() if payload.get("location") else "Unknown",
            normalized_location=normalized_location,
            is_remote=payload.get("is_remote", False),
            remote_type=remote_type,
            description=payload.get("description", "").strip() if payload.get("description") else "",
            requirements=payload.get("requirements", "").strip() if payload.get("requirements") else None,
            responsibilities=payload.get("responsibilities", "").strip() if payload.get("responsibilities") else None,
            salary_min=payload.get("salary_min"),
            salary_max=payload.get("salary_max"),
            salary_currency=payload.get("salary_currency", "USD").upper(),
            salary_period=payload.get("salary_period"),
            salary_yearly_min=yearly_min,
            salary_yearly_max=yearly_max,
            experience_level=normalize_experience_level(payload.get("experience_level")),
            employment_type=normalize_employment_type(payload.get("employment_type")),
            source=raw_record.source_name,
            source_url=payload.get("source_url", ""),
            source_job_id=payload.get("source_job_id", raw_record.external_id),
            posted_date=posted_date,
            expires_date=expires_date,
            application_url=payload.get("application_url"),
            application_email=payload.get("application_email"),
            skills=skills,
            keywords=keywords,
            quality_score=payload.get("quality_score", 0.0),
            raw_record=raw_record,
        )

    def normalize_batch(self, raw_records: List[RawDataRecord]) -> List[NormalizedJob]:
        """Normalize multiple raw job records."""
        return [self.normalize(record) for record in raw_records]