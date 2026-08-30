"""
Data Pipeline Package for CareerIntel AI.

This package provides a structured, validated, and source-aware
real-world data ingestion system.
"""

from backend.data_pipeline.collectors.base_collector import BaseCollector, RawDataRecord, CollectorHealth
from backend.data_pipeline.collectors import (
    MockJobCollector, MockCompanyCollector, MockNewsCollector, 
    MockResearchCollector, MockSkillCollector, MockCourseCollector,
    MockMarketTrendCollector
)
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
from backend.data_pipeline.deduplication.duplicate_detector import DuplicateDetector, DuplicateMatch
from backend.data_pipeline.pipeline.ingestion_pipeline import IngestionPipeline, PipelineResult, PipelineStage, PipelineStageResult
from backend.data_pipeline.sources.source_registry import SourceRegistry, SourceConfig, SourceType, SourceProviderType
from backend.evaluation.data_quality import DataQualityScorer, DataQualityResult, QualityDimension, DataSourceType, FreshnessTier, create_default_scorer

__all__ = [
    "BaseCollector",
    "RawDataRecord",
    "CollectorHealth",
    "MockJobCollector",
    "MockCompanyCollector",
    "MockNewsCollector",
    "MockResearchCollector",
    "MockSkillCollector",
    "MockCourseCollector",
    "MockMarketTrendCollector",
    "JobNormalizer",
    "NormalizedJob",
    "CompanyNormalizer",
    "NormalizedCompany",
    "NewsNormalizer",
    "NormalizedNews",
    "ResearchNormalizer",
    "NormalizedResearch",
    "SkillNormalizer",
    "NormalizedSkill",
    "SkillCategory",
    "SkillLevel",
    "classify_skill_category",
    "normalize_skill_name",
    "extract_related_skills",
    "CourseNormalizer",
    "NormalizedCourse",
    "CourseLevel",
    "CourseProvider",
    "normalize_course_level",
    "normalize_provider",
    "MarketTrendNormalizer",
    "NormalizedMarketTrend",
    "DemandSignal",
    "TrendDirection",
    "normalize_demand_signal",
    "normalize_trend_direction",
    "DuplicateDetector",
    "DuplicateMatch",
    "IngestionPipeline",
    "PipelineResult",
    "PipelineStage",
    "PipelineStageResult",
    "SourceRegistry",
    "SourceConfig",
    "SourceType",
    "SourceProviderType",
    "DataQualityScorer",
    "DataQualityResult",
    "QualityDimension",
    "DataSourceType",
    "FreshnessTier",
    "create_default_scorer",
]