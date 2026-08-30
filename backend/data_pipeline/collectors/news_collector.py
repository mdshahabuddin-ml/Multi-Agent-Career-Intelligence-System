"""
Mock news collector for development and testing.
"""

import asyncio
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from backend.data_pipeline.collectors.base_collector import BaseCollector, RawDataRecord, CollectorHealth


class MockNewsCollector(BaseCollector):
    """Mock news collector for development/testing."""
    
    MOCK_ARTICLES = [
        {
            "title": "AI Job Market Booms as Companies Race to Hire ML Engineers",
            "summary": "Demand for machine learning engineers has surged 300% year-over-year as enterprises accelerate AI adoption.",
            "content": "The artificial intelligence job market is experiencing unprecedented growth. Companies across all sectors are competing aggressively for machine learning talent. According to recent data, job postings for ML engineers have increased 300% compared to last year. Tech giants like Google, Microsoft, and Amazon are leading the hiring spree, but traditional enterprises in finance, healthcare, and manufacturing are also building AI teams. Salaries for senior ML engineers now routinely exceed $200,000 base, with total compensation packages reaching $400,000+ at top firms. The talent shortage has sparked a wave of upskilling programs and university partnerships.",
            "source_article_id": "mock_news_1",
            "source_url": "https://example.com/news/ai-job-market-boom",
            "author": "Sarah Chen",
            "published_date": (datetime.utcnow() - timedelta(days=1)).isoformat(),
            "topics": ["ai_ml", "hiring", "salary"],
            "companies_mentioned": ["Google", "Microsoft", "Amazon"],
            "technologies_mentioned": ["Python", "TensorFlow", "PyTorch", "Kubernetes"],
            "sentiment": "positive",
            "language": "en",
            "quality_score": 0.9,
        },
        {
            "title": "Major Tech Layoffs Continue: 50,000+ Jobs Cut in 2024",
            "summary": "Leading technology companies announce another round of workforce reductions amid economic uncertainty.",
            "content": "The tech industry continues to face significant workforce reductions. Over 50,000 employees have been laid off across major technology companies in the first half of 2024. Companies cite over-hiring during the pandemic, rising interest rates, and shifting priorities toward AI investments as key drivers. Meta, Google, Amazon, and Microsoft have all announced multiple rounds of cuts. However, AI and machine learning roles remain relatively insulated, with some companies actually increasing hiring in these areas while cutting elsewhere. The disconnect highlights the strategic pivot toward artificial intelligence across the sector.",
            "source_article_id": "mock_news_2",
            "source_url": "https://example.com/news/tech-layoffs-2024",
            "author": "James Rodriguez",
            "published_date": (datetime.utcnow() - timedelta(days=2)).isoformat(),
            "topics": ["hiring", "big_tech", "ai_ml"],
            "companies_mentioned": ["Meta", "Google", "Amazon", "Microsoft"],
            "technologies_mentioned": ["AI", "Machine Learning"],
            "sentiment": "negative",
            "language": "en",
            "quality_score": 0.85,
        },
        {
            "title": "Remote Work Policies Stabilize: Hybrid Becomes Dominant Model",
            "summary": "Survey of 5,000 tech companies shows hybrid work (3 days office) is now the standard arrangement.",
            "content": "A comprehensive survey of 5,000 technology companies reveals that hybrid work has solidified as the dominant model. 65% of companies now require 2-3 days in office per week, while only 15% are fully remote and 20% fully in-office. The shift reflects a compromise between employee preferences for flexibility and company desires for collaboration. Companies with flexible policies report 23% higher retention rates and 18% better candidate attraction. However, fully remote companies continue to access broader talent pools and report lower real estate costs.",
            "source_article_id": "mock_news_3",
            "source_url": "https://example.com/news/remote-work-hybrid-standard",
            "author": "Maria Santos",
            "published_date": (datetime.utcnow() - timedelta(days=3)).isoformat(),
            "topics": ["remote_work", "hiring"],
            "companies_mentioned": [],
            "technologies_mentioned": [],
            "sentiment": "neutral",
            "language": "en",
            "quality_score": 0.88,
        },
        {
            "title": "Cloud Computing Skills Gap Widens as Multi-Cloud Adoption Accelerates",
            "summary": "Enterprises struggle to find talent with expertise across AWS, Azure, and GCP simultaneously.",
            "content": "The rapid adoption of multi-cloud strategies has created a severe skills gap in cloud computing. 78% of enterprises now use two or more cloud providers, but only 12% of cloud professionals have certified expertise across multiple platforms. This mismatch is driving up salaries for multi-cloud architects, with compensation packages 35% higher than single-cloud specialists. Companies are responding with internal training programs, but the pace of cloud innovation makes it difficult for training to keep up. Kubernetes, Terraform, and cross-cloud networking are the most sought-after skills.",
            "source_article_id": "mock_news_4",
            "source_url": "https://example.com/news/cloud-skills-gap",
            "author": "David Kim",
            "published_date": (datetime.utcnow() - timedelta(days=4)).isoformat(),
            "topics": ["cloud", "hiring", "salary"],
            "companies_mentioned": ["AWS", "Azure", "GCP"],
            "technologies_mentioned": ["Kubernetes", "Terraform", "Docker", "AWS", "GCP", "Azure"],
            "sentiment": "neutral",
            "language": "en",
            "quality_score": 0.92,
        },
        {
            "title": "Startup Funding Rebounds in Q2 2024, AI Companies Lead",
            "summary": "Venture capital investment increases 45% quarter-over-quarter, with AI startups capturing 60% of total funding.",
            "content": "Venture capital funding showed strong recovery in Q2 2024, with total investment reaching $85 billion globally - a 45% increase from Q1. Artificial intelligence companies dominated, securing 60% of all venture dollars. Generative AI infrastructure, AI applications, and AI-powered developer tools were the hottest categories. The rebound signals renewed investor confidence after a challenging 2023. However, deal count remains below peak levels, indicating investors are writing larger checks to fewer companies. Series A and B rounds saw the strongest growth.",
            "source_article_id": "mock_news_5",
            "source_url": "https://example.com/news/startup-funding-rebound",
            "author": "Lisa Wang",
            "published_date": (datetime.utcnow() - timedelta(days=5)).isoformat(),
            "topics": ["startup", "ai_ml", "funding"],
            "companies_mentioned": ["OpenAI", "Anthropic", "NVIDIA"],
            "technologies_mentioned": ["Generative AI", "LLM", "Transformers"],
            "sentiment": "positive",
            "language": "en",
            "quality_score": 0.87,
        },
    ]

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._source_name = "mock_news"
        self._source_type = "internal_database"
        self._delay = self.config.get("delay", 0.1)
        self._failure_rate = self.config.get("failure_rate", 0.0)
    
    @property
    def source_name(self) -> str:
        return self._source_name
    
    @property
    def source_type(self) -> str:
        return self._source_type

    async def fetch(self, query: str = "", topic: Optional[str] = None, 
                    company: Optional[str] = None, days_back: int = 30,
                    limit: int = 50, **kwargs) -> List[Dict[str, Any]]:
        """Return mock news data for testing."""
        await asyncio.sleep(self._delay)
        
        if self._failure_rate > 0 and random.random() < self._failure_rate:
            raise ConnectionError("Simulated collector failure")
        
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)
        filtered = []
        query_lower = query.lower()
        
        for article in self.MOCK_ARTICLES:
            pub_date = datetime.fromisoformat(article["published_date"].replace("Z", "+00:00"))
            if pub_date < cutoff_date:
                continue
            
            if query_lower and not (
                query_lower in article["title"].lower() or
                query_lower in article["summary"].lower() or
                query_lower in article["content"].lower()
            ):
                continue
            
            if topic and topic not in article["topics"]:
                continue
            
            if company and company.lower() not in [c.lower() for c in article["companies_mentioned"]]:
                continue
            
            filtered.append(article.copy())
            
            if len(filtered) >= limit:
                break
        
        return filtered

    async def parse(self, raw_data: List[Dict[str, Any]]) -> List[RawDataRecord]:
        """Parse raw mock data into RawDataRecord objects."""
        records = []
        for article in raw_data:
            record = RawDataRecord.create(
                source_id="mock_news",
                source_name="Mock News Provider",
                source_type="internal_database",
                external_id=article["source_article_id"],
                source_url=article["source_url"],
                raw_payload=article,
                metadata={"mock": True}
            )
            records.append(record)
        return records

    async def health_check(self) -> CollectorHealth:
        """Mock collector is always healthy."""
        return CollectorHealth.HEALTHY