"""
Mock market trend collector for development and testing.
"""

import asyncio
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from backend.data_pipeline.collectors.base_collector import BaseCollector, RawDataRecord, CollectorHealth


class MockMarketTrendCollector(BaseCollector):
    """Mock market trend collector for development/testing."""
    
    MOCK_TRENDS = [
        {
            "skill": "Python",
            "technology": "Python",
            "role": "Software Engineer",
            "location": "United States",
            "demand_signal": "job_postings",
            "signal_value": 15420,
            "trend_direction": "rising",
            "time_period": "monthly",
            "period_start": (datetime.utcnow() - timedelta(days=30)).isoformat(),
            "period_end": datetime.utcnow().isoformat(),
            "source_count": 5,
            "source_quality": 0.85,
            "evidence": [
                {"source": "linkedin", "count": 8500, "quality": 0.9},
                {"source": "indeed", "count": 4200, "quality": 0.8},
                {"source": "glassdoor", "count": 2720, "quality": 0.85},
            ],
            "confidence_score": 0.88,
            "calculated_at": datetime.utcnow().isoformat(),
            "source_trend_id": "trend_python_jobs_us",
            "source_url": "https://example.com/trends/python-jobs-us",
            "quality_score": 0.9,
        },
        {
            "skill": "Kubernetes",
            "technology": "Kubernetes",
            "role": "DevOps Engineer",
            "location": "Global",
            "demand_signal": "job_postings",
            "signal_value": 8750,
            "trend_direction": "rising",
            "time_period": "monthly",
            "period_start": (datetime.utcnow() - timedelta(days=30)).isoformat(),
            "period_end": datetime.utcnow().isoformat(),
            "source_count": 4,
            "source_quality": 0.82,
            "evidence": [
                {"source": "linkedin", "count": 4200, "quality": 0.9},
                {"source": "indeed", "count": 2800, "quality": 0.8},
                {"source": "glassdoor", "count": 1750, "quality": 0.85},
            ],
            "confidence_score": 0.85,
            "calculated_at": datetime.utcnow().isoformat(),
            "source_trend_id": "trend_kubernetes_jobs_global",
            "source_url": "https://example.com/trends/kubernetes-jobs-global",
            "quality_score": 0.88,
        },
        {
            "skill": "Machine Learning",
            "technology": "TensorFlow",
            "role": "ML Engineer",
            "location": "United States",
            "demand_signal": "salary_trends",
            "signal_value": 185000,
            "trend_direction": "rising",
            "time_period": "quarterly",
            "period_start": (datetime.utcnow() - timedelta(days=90)).isoformat(),
            "period_end": datetime.utcnow().isoformat(),
            "source_count": 3,
            "source_quality": 0.88,
            "evidence": [
                {"source": "levels.fyi", "median": 185000, "quality": 0.9},
                {"source": "glassdoor", "median": 178000, "quality": 0.85},
                {"source": "h1b_data", "median": 182000, "quality": 0.9},
            ],
            "confidence_score": 0.87,
            "calculated_at": datetime.utcnow().isoformat(),
            "source_trend_id": "trend_ml_salary_us",
            "source_url": "https://example.com/trends/ml-salary-us",
            "quality_score": 0.92,
        },
        {
            "skill": "React",
            "technology": "React",
            "role": "Frontend Developer",
            "location": "Europe",
            "demand_signal": "job_postings",
            "signal_value": 12300,
            "trend_direction": "stable",
            "time_period": "monthly",
            "period_start": (datetime.utcnow() - timedelta(days=30)).isoformat(),
            "period_end": datetime.utcnow().isoformat(),
            "source_count": 4,
            "source_quality": 0.8,
            "evidence": [
                {"source": "linkedin", "count": 6500, "quality": 0.9},
                {"source": "indeed", "count": 3800, "quality": 0.8},
                {"source": "glassdoor", "count": 2000, "quality": 0.85},
            ],
            "confidence_score": 0.83,
            "calculated_at": datetime.utcnow().isoformat(),
            "source_trend_id": "trend_react_jobs_eu",
            "source_url": "https://example.com/trends/react-jobs-eu",
            "quality_score": 0.87,
        },
        {
            "skill": "Rust",
            "technology": "Rust",
            "role": "Systems Engineer",
            "location": "Global",
            "demand_signal": "skill_mentions",
            "signal_value": 3420,
            "trend_direction": "rising",
            "time_period": "monthly",
            "period_start": (datetime.utcnow() - timedelta(days=30)).isoformat(),
            "period_end": datetime.utcnow().isoformat(),
            "source_count": 3,
            "source_quality": 0.75,
            "evidence": [
                {"source": "github", "mentions": 1800, "quality": 0.8},
                {"source": "stackoverflow", "mentions": 920, "quality": 0.7},
                {"source": "hackernews", "mentions": 700, "quality": 0.75},
            ],
            "confidence_score": 0.78,
            "calculated_at": datetime.utcnow().isoformat(),
            "source_trend_id": "trend_rust_mentions_global",
            "source_url": "https://example.com/trends/rust-mentions-global",
            "quality_score": 0.82,
        },
        {
            "skill": "Generative AI",
            "technology": "LLM",
            "role": "AI Engineer",
            "location": "United States",
            "demand_signal": "job_postings",
            "signal_value": 4200,
            "trend_direction": "rising",
            "time_period": "monthly",
            "period_start": (datetime.utcnow() - timedelta(days=30)).isoformat(),
            "period_end": datetime.utcnow().isoformat(),
            "source_count": 5,
            "source_quality": 0.9,
            "evidence": [
                {"source": "linkedin", "count": 2100, "quality": 0.95},
                {"source": "indeed", "count": 1200, "quality": 0.85},
                {"source": "glassdoor", "count": 900, "quality": 0.9},
            ],
            "confidence_score": 0.92,
            "calculated_at": datetime.utcnow().isoformat(),
            "source_trend_id": "trend_genai_jobs_us",
            "source_url": "https://example.com/trends/genai-jobs-us",
            "quality_score": 0.95,
        },
    ]

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._source_name = "mock_market_trends"
        self._source_type = "internal_database"
        self._delay = self.config.get("delay", 0.1)
        self._failure_rate = self.config.get("failure_rate", 0.0)
    
    @property
    def source_name(self) -> str:
        return self._source_name
    
    @property
    def source_type(self) -> str:
        return self._source_type

    async def fetch(self, query: str = "", skill: Optional[str] = None, 
                    location: Optional[str] = None, demand_signal: Optional[str] = None,
                    limit: int = 50, **kwargs) -> List[Dict[str, Any]]:
        """Return mock market trend data for testing."""
        await asyncio.sleep(self._delay)
        
        if self._failure_rate > 0 and random.random() < self._failure_rate:
            raise ConnectionError("Simulated collector failure")
        
        filtered = []
        query_lower = query.lower()
        
        for trend in self.MOCK_TRENDS:
            if query_lower and not (
                query_lower in trend["skill"].lower() or
                query_lower in trend.get("technology", "").lower() or
                query_lower in trend.get("role", "").lower()
            ):
                continue
            
            if skill and skill.lower() != trend["skill"].lower():
                continue
            
            if location and location.lower() != trend.get("location", "").lower():
                continue
            
            if demand_signal and demand_signal != trend.get("demand_signal"):
                continue
            
            filtered.append(trend.copy())
            
            if len(filtered) >= limit:
                break
        
        return filtered

    async def parse(self, raw_data: List[Dict[str, Any]]) -> List[RawDataRecord]:
        """Parse raw mock data into RawDataRecord objects."""
        records = []
        for trend in raw_data:
            record = RawDataRecord.create(
                source_id="mock_market_trends",
                source_name="Mock Market Trend Provider",
                source_type="internal_database",
                external_id=trend["source_trend_id"],
                source_url=trend["source_url"],
                raw_payload=trend,
                metadata={"mock": True}
            )
            records.append(record)
        return records

    async def health_check(self) -> CollectorHealth:
        """Mock collector is always healthy."""
        return CollectorHealth.HEALTHY