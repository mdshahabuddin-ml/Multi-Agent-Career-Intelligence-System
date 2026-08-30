"""
Normalization modules for transforming raw data to standard format.
"""

from backend.data_pipeline.normalization.job_normalizer import JobNormalizer, NormalizedJob
from backend.data_pipeline.normalization.company_normalizer import CompanyNormalizer, NormalizedCompany
from backend.data_pipeline.normalization.news_normalizer import NewsNormalizer, NormalizedNews
from backend.data_pipeline.normalization.research_normalizer import ResearchNormalizer, NormalizedResearch
from backend.data_pipeline.normalization.skill_normalizer import (
    SkillNormalizer, NormalizedSkill, SkillCategory, SkillLevel,
    classify_skill_category, normalize_skill_name, extract_related_skills,
)
from backend.data_pipeline.normalization.course_normalizer import (
    CourseNormalizer, NormalizedCourse, CourseLevel, CourseProvider,
    normalize_course_level, normalize_provider,
)
from backend.data_pipeline.normalization.market_trend_normalizer import (
    MarketTrendNormalizer, NormalizedMarketTrend, DemandSignal, TrendDirection,
    normalize_demand_signal, normalize_trend_direction,
)

__all__ = [
    "JobNormalizer", "NormalizedJob",
    "CompanyNormalizer", "NormalizedCompany",
    "NewsNormalizer", "NormalizedNews",
    "ResearchNormalizer", "NormalizedResearch",
    "SkillNormalizer", "NormalizedSkill",
    "SkillCategory", "SkillLevel",
    "classify_skill_category", "normalize_skill_name", "extract_related_skills",
    "CourseNormalizer", "NormalizedCourse",
    "CourseLevel", "CourseProvider",
    "normalize_course_level", "normalize_provider",
    "MarketTrendNormalizer", "NormalizedMarketTrend",
    "DemandSignal", "TrendDirection",
    "normalize_demand_signal", "normalize_trend_direction",
]