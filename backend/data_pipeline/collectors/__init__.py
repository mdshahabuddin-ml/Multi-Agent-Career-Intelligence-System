"""
Collector modules for data ingestion.
"""

from backend.data_pipeline.collectors.base_collector import BaseCollector, RawDataRecord, CollectorHealth
from backend.data_pipeline.collectors.mock_collector import MockJobCollector
from backend.data_pipeline.collectors.company_collector import MockCompanyCollector
from backend.data_pipeline.collectors.news_collector import MockNewsCollector
from backend.data_pipeline.collectors.research_collector import MockResearchCollector
from backend.data_pipeline.collectors.skill_collector import MockSkillCollector
from backend.data_pipeline.collectors.course_collector import MockCourseCollector
from backend.data_pipeline.collectors.market_trend_collector import MockMarketTrendCollector

__all__ = [
    "BaseCollector", "RawDataRecord", "CollectorHealth",
    "MockJobCollector", "MockCompanyCollector", "MockNewsCollector", 
    "MockResearchCollector", "MockSkillCollector", "MockCourseCollector",
    "MockMarketTrendCollector",
]