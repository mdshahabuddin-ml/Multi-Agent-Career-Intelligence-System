import logging
import re
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum as PyEnum

from backend.data_pipeline.collectors.base_collector import RawDataRecord

logger = logging.getLogger(__name__)


class CourseLevel(str, PyEnum):
    """Course difficulty levels."""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    ALL_LEVELS = "all_levels"


class CourseProvider(str, PyEnum):
    """Known course providers."""
    COURSERA = "coursera"
    EDX = "edx"
    UDEMY = "udemy"
    PLURALSIGHT = "pluralsight"
    LINKEDIN_LEARNING = "linkedin_learning"
    KHAN_ACADEMY = "khan_academy"
    FREECODECAMP = "freecodecamp"
    YOUTUBE = "youtube"
    UNIVERSITY = "university"
    BOOTCAMP = "bootcamp"
    OTHER = "other"


@dataclass
class NormalizedCourse:
    """Normalized course/learning resource data."""
    title: str
    provider: CourseProvider
    provider_name: str
    url: str
    description: Optional[str]
    skills: List[str]
    technologies: List[str]
    level: CourseLevel
    duration_hours: Optional[float]
    duration_weeks: Optional[int]
    price: Optional[float]
    currency: str
    is_free: bool
    certificate_available: bool
    language: str
    prerequisites: List[str]
    learning_outcomes: List[str]
    source: str
    source_url: str
    source_course_id: str
    published_date: Optional[datetime]
    retrieved_date: datetime
    rating: Optional[float]
    review_count: Optional[int]
    enrollment_count: Optional[int]
    quality_score: float
    raw_record: Optional[RawDataRecord] = None


def normalize_course_level(level: Optional[str]) -> CourseLevel:
    """Normalize course level to standard enum."""
    if not level:
        return CourseLevel.ALL_LEVELS
    level_lower = level.lower().strip()
    
    if level_lower in ["beginner", "introductory", "entry", "fundamentals", "basics"]:
        return CourseLevel.BEGINNER
    elif level_lower in ["intermediate", "mid", "some experience"]:
        return CourseLevel.INTERMEDIATE
    elif level_lower in ["advanced", "expert", "professional", "mastery"]:
        return CourseLevel.ADVANCED
    elif level_lower in ["all", "all levels", "any"]:
        return CourseLevel.ALL_LEVELS
    return CourseLevel.ALL_LEVELS


def normalize_provider(provider: Optional[str]) -> CourseProvider:
    """Normalize provider name to standard enum."""
    if not provider:
        return CourseProvider.OTHER
    provider_lower = provider.lower().strip()
    
    provider_map = {
        "coursera": CourseProvider.COURSERA,
        "edx": CourseProvider.EDX,
        "udemy": CourseProvider.UDEMY,
        "pluralsight": CourseProvider.PLURALSIGHT,
        "linkedin": CourseProvider.LINKEDIN_LEARNING,
        "linkedin learning": CourseProvider.LINKEDIN_LEARNING,
        "khan academy": CourseProvider.KHAN_ACADEMY,
        "freecodecamp": CourseProvider.FREECODECAMP,
        "free code camp": CourseProvider.FREECODECAMP,
        "youtube": CourseProvider.YOUTUBE,
        "university": CourseProvider.UNIVERSITY,
        "bootcamp": CourseProvider.BOOTCAMP,
        "boot camp": CourseProvider.BOOTCAMP,
    }
    
    return provider_map.get(provider_lower, CourseProvider.OTHER)


def extract_prerequisites(text: str) -> List[str]:
    """Extract prerequisites from text."""
    text_lower = text.lower()
    prereqs = []
    
    prereq_keywords = [
        "prerequisite", "prerequisites", "required", "requirements",
        "should know", "must know", "need to know", "prior knowledge",
        "background in", "experience with", "familiarity with",
    ]
    
    for kw in prereq_keywords:
        if kw in text_lower:
            # Find the sentence containing the keyword
            sentences = re.split(r'[.!?]', text)
            for sent in sentences:
                if kw in sent.lower():
                    prereqs.append(sent.strip())
                    break
    
    return prereqs[:5]


class CourseNormalizer:
    """Normalize course/learning resource data from various sources."""

    def __init__(self):
        self.name = "course_normalizer"

    def normalize(self, raw_record: RawDataRecord) -> NormalizedCourse:
        """Normalize a single raw course record."""
        payload = raw_record.raw_payload
        logger.debug(f"Normalizing course: {payload.get('title')}")

        title = payload.get("title", "").strip()
        provider = normalize_provider(payload.get("provider"))
        provider_name = payload.get("provider_name", "").strip() or provider.value.title()
        url = payload.get("url", "").strip()
        
        description = payload.get("description", "").strip() if payload.get("description") else None
        
        skills = payload.get("skills") or []
        technologies = payload.get("technologies") or []
        
        level = normalize_course_level(payload.get("level"))
        
        duration_hours = payload.get("duration_hours")
        if isinstance(duration_hours, str):
            try:
                duration_hours = float(duration_hours)
            except Exception:
                duration_hours = None
        
        duration_weeks = payload.get("duration_weeks")
        if isinstance(duration_weeks, str):
            try:
                duration_weeks = int(duration_weeks)
            except Exception:
                duration_weeks = None
        
        price = payload.get("price")
        if isinstance(price, str):
            try:
                price = float(price.replace("$", "").replace(",", ""))
            except Exception:
                price = None
        
        currency = payload.get("currency", "USD").upper()
        is_free = payload.get("is_free", price is None or price == 0)
        certificate_available = payload.get("certificate_available", False)
        
        language = payload.get("language", "en")
        
        prerequisites = payload.get("prerequisites") or extract_prerequisites(
            (description or "") + " " + " ".join(skills)
        )
        
        learning_outcomes = payload.get("learning_outcomes") or []
        
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
        
        rating = payload.get("rating")
        if isinstance(rating, str):
            try:
                rating = float(rating)
            except Exception:
                rating = None
        
        review_count = payload.get("review_count")
        if isinstance(review_count, str):
            try:
                review_count = int(review_count.replace(",", ""))
            except Exception:
                review_count = None
        
        enrollment_count = payload.get("enrollment_count")
        if isinstance(enrollment_count, str):
            try:
                enrollment_count = int(enrollment_count.replace(",", "").replace("k", "000"))
            except Exception:
                enrollment_count = None

        return NormalizedCourse(
            title=title,
            provider=provider,
            provider_name=provider_name,
            url=url,
            description=description,
            skills=skills,
            technologies=technologies,
            level=level,
            duration_hours=duration_hours,
            duration_weeks=duration_weeks,
            price=price,
            currency=currency,
            is_free=is_free,
            certificate_available=certificate_available,
            language=language,
            prerequisites=prerequisites,
            learning_outcomes=learning_outcomes,
            source=raw_record.source_name,
            source_url=url,
            source_course_id=payload.get("source_course_id", raw_record.external_id),
            published_date=published_date,
            retrieved_date=retrieved_date,
            rating=rating,
            review_count=review_count,
            enrollment_count=enrollment_count,
            quality_score=payload.get("quality_score", 0.0),
            raw_record=raw_record,
        )

    def normalize_batch(self, raw_records: List[RawDataRecord]) -> List[NormalizedCourse]:
        """Normalize multiple raw course records."""
        return [self.normalize(record) for record in raw_records]