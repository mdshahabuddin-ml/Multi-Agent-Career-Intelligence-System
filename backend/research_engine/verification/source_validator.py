from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum as PyEnum
from urllib.parse import urlparse
import logging
import re

from backend.research_engine.state.research_context import SourceMetadata, ResearchSourceType

logger = logging.getLogger(__name__)


class ValidationLevel(str, PyEnum):
    """Validation strictness levels."""
    STRICT = "strict"
    MODERATE = "moderate"
    LENIENT = "lenient"


@dataclass
class ValidationResult:
    """Result of source validation."""
    source_url: str
    is_valid: bool
    credibility_score: float
    quality_score: float
    validation_level: ValidationLevel
    checks: Dict[str, Any]
    warnings: List[str]
    errors: List[str]
    validated_at: datetime = field(default_factory=datetime.utcnow)


class SourceValidator:
    """Validate source credibility and quality."""

    # Known high-credibility domains
    HIGH_CREDIBILITY_DOMAINS = {
        # Academic
        "arxiv.org", "pubmed.ncbi.nlm.nih.gov", "scholar.google.com",
        "doi.org", "researchgate.net", "academia.edu",
        # Government
        "gov", "gov.uk", "europa.eu", "who.int", "un.org",
        # Reputable news
        "reuters.com", "apnews.com", "bbc.com", "nytimes.com",
        "wsj.com", "ft.com", "economist.com", "bloomberg.com",
        # Tech
        "github.com", "stackoverflow.com", "developer.mozilla.org",
        "aws.amazon.com", "cloud.google.com", "azure.microsoft.com",
        # Professional
        "linkedin.com", "glassdoor.com", "indeed.com",
    }

    MEDIUM_CREDIBILITY_DOMAINS = {
        "wikipedia.org", "medium.com", "substack.com",
        "reddit.com", "quora.com", "hackernews.com",
    }

    LOW_CREDIBILITY_TLDS = {".xyz", ".top", ".club", ".online", ".site", ".info"}

    def __init__(self, validation_level: ValidationLevel = ValidationLevel.MODERATE):
        self.validation_level = validation_level

    def validate(self, source: SourceMetadata) -> ValidationResult:
        """Validate a source."""
        checks = {}
        warnings = []
        errors = []

        # URL validation
        url_check = self._validate_url(source.url)
        checks["url"] = url_check
        if not url_check["valid"]:
            errors.append(url_check["error"])

        # Domain credibility
        domain_check = self._check_domain_credibility(source)
        checks["domain"] = domain_check
        if domain_check["score"] < 0.4:
            warnings.append(f"Low credibility domain: {domain_check.get('domain', 'unknown')}")

        # Content quality
        content_check = self._check_content_quality(source)
        checks["content"] = content_check
        if content_check["score"] < 0.3:
            warnings.append("Low content quality indicators")

        # Recency
        recency_check = self._check_recency(source)
        checks["recency"] = recency_check
        days_old = recency_check.get("days_old")
        if days_old is not None and days_old > 365:
            warnings.append(f"Source is {days_old} days old")

        # Author verification
        author_check = self._check_author(source)
        checks["author"] = author_check

        # HTTPS
        https_check = self._check_https(source.url)
        checks["https"] = https_check
        if not https_check["valid"]:
            warnings.append("Source does not use HTTPS")

        # Calculate scores
        credibility_score = self._calculate_credibility(checks)
        quality_score = self._calculate_quality(checks)

        # Determine validity
        is_valid = len(errors) == 0 and credibility_score >= self._min_credibility_threshold()

        return ValidationResult(
            source_url=source.url,
            is_valid=is_valid,
            credibility_score=credibility_score,
            quality_score=quality_score,
            validation_level=self.validation_level,
            checks=checks,
            warnings=warnings,
            errors=errors,
        )

    def _validate_url(self, url: str) -> Dict[str, Any]:
        """Validate URL format."""
        try:
            parsed = urlparse(url)
            valid = bool(parsed.scheme and parsed.netloc)
            return {
                "valid": valid,
                "scheme": parsed.scheme,
                "netloc": parsed.netloc,
                "path": parsed.path,
            }
        except Exception as e:
            return {"valid": False, "error": str(e)}

    def _check_domain_credibility(self, source: SourceMetadata) -> Dict[str, Any]:
        """Check domain credibility."""
        domain = source.domain or urlparse(source.url).netloc.lower()
        domain = domain.replace("www.", "")

        score = 0.5  # Base score

        if any(d in domain for d in self.HIGH_CREDIBILITY_DOMAINS):
            score = 0.9
            tier = "high"
        elif any(d in domain for d in self.MEDIUM_CREDIBILITY_DOMAINS):
            score = 0.6
            tier = "medium"
        elif domain.endswith((".edu", ".gov", ".org")):
            score = 0.8
            tier = "high"
        elif domain.endswith(".com"):
            score = 0.7
            tier = "medium"
        elif any(domain.endswith(tld) for tld in self.LOW_CREDIBILITY_TLDS):
            score = 0.3
            tier = "low"
        else:
            tier = "unknown"

        # Check source type bonus
        type_bonus = {
            ResearchSourceType.ACADEMIC: 0.1,
            ResearchSourceType.GOVERNMENT: 0.1,
            ResearchSourceType.COMPANY: 0.05,
        }.get(source.source_type, 0)

        final_score = min(score + type_bonus, 1.0)

        return {
            "score": final_score,
            "domain": domain,
            "tier": tier,
            "type_bonus": type_bonus,
        }

    def _check_content_quality(self, source: SourceMetadata) -> Dict[str, Any]:
        """Check content quality indicators."""
        word_count = source.word_count
        has_title = bool(source.title and len(source.title) > 10)
        has_author = bool(source.author)
        has_date = bool(source.published_date)
        has_snippet = bool(source.custom_metadata.get("snippet") or source.custom_metadata.get("content"))

        score = 0.0
        if word_count > 1000:
            score += 0.3
        elif word_count > 500:
            score += 0.2
        elif word_count > 100:
            score += 0.1

        if has_title:
            score += 0.2
        if has_author:
            score += 0.2
        if has_date:
            score += 0.1
        if has_snippet:
            score += 0.2

        return {
            "score": min(score, 1.0),
            "word_count": word_count,
            "has_title": has_title,
            "has_author": has_author,
            "has_date": has_date,
            "has_content": has_snippet,
        }

    def _check_recency(self, source: SourceMetadata) -> Dict[str, Any]:
        """Check how recent the source is."""
        if not source.published_date:
            return {"score": 0.3, "days_old": None, "warning": "No publication date"}

        try:
            from datetime import datetime, timezone
            pub_date = source.published_date
            if pub_date.tzinfo is None:
                pub_date = pub_date.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            days_old = (now - pub_date).days

            if days_old < 7:
                score = 1.0
            elif days_old < 30:
                score = 0.9
            elif days_old < 90:
                score = 0.8
            elif days_old < 180:
                score = 0.7
            elif days_old < 365:
                score = 0.5
            else:
                score = 0.3

            return {
                "score": score,
                "days_old": days_old,
                "published_date": source.published_date.isoformat(),
            }
        except Exception:
            return {"score": 0.3, "days_old": None, "error": "Date parsing failed"}

    def _check_author(self, source: SourceMetadata) -> Dict[str, Any]:
        """Check author credibility."""
        if not source.author:
            return {"score": 0.4, "has_author": False}

        # In production, could check author credentials
        return {
            "score": 0.7,
            "has_author": True,
            "author": source.author,
        }

    def _check_https(self, url: str) -> Dict[str, Any]:
        """Check if URL uses HTTPS."""
        try:
            parsed = urlparse(url)
            is_https = parsed.scheme == "https"
            return {
                "valid": is_https,
                "scheme": parsed.scheme,
            }
        except Exception:
            return {"valid": False}

    def _calculate_credibility(self, checks: Dict[str, Any]) -> float:
        """Calculate overall credibility score."""
        weights = {
            "domain": 0.35,
            "content": 0.20,
            "recency": 0.15,
            "author": 0.10,
            "https": 0.05,
            "url": 0.15,
        }

        score = 0.0
        for key, weight in weights.items():
            check = checks.get(key, {})
            score += check.get("score", 0) * weight

        return min(score, 1.0)

    def _calculate_quality(self, checks: Dict[str, Any]) -> float:
        """Calculate content quality score."""
        weights = {
            "content": 0.5,
            "domain": 0.2,
            "recency": 0.15,
            "author": 0.15,
        }

        score = 0.0
        for key, weight in weights.items():
            check = checks.get(key, {})
            score += check.get("score", 0) * weight

        return min(score, 1.0)

    def _min_credibility_threshold(self) -> float:
        """Get minimum credibility threshold based on validation level."""
        thresholds = {
            ValidationLevel.STRICT: 0.7,
            ValidationLevel.MODERATE: 0.5,
            ValidationLevel.LENIENT: 0.3,
        }
        return thresholds.get(self.validation_level, 0.5)

    def validate_batch(self, sources: List[SourceMetadata]) -> List[ValidationResult]:
        """Validate multiple sources."""
        return [self.validate(source) for source in sources]

    def filter_valid_sources(self, sources: List[SourceMetadata]) -> List[SourceMetadata]:
        """Filter to only valid sources."""
        validated = self.validate_batch(sources)
        return [s for s, v in zip(sources, validated) if v.is_valid]