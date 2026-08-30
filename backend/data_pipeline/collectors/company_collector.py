"""
Mock company collector for development and testing.
"""

import asyncio
import random
from datetime import datetime
from typing import List, Dict, Any, Optional

from backend.data_pipeline.collectors.base_collector import BaseCollector, RawDataRecord, CollectorHealth


class MockCompanyCollector(BaseCollector):
    """Mock company collector for development/testing."""
    
    MOCK_COMPANIES = [
        {
            "name": "TechCorp",
            "domain": "techcorp.com",
            "description": "Leading technology company building innovative cloud solutions for enterprises.",
            "industry": "Technology",
            "company_size": "1001-5000",
            "headquarters": "San Francisco, CA",
            "founded_year": 2010,
            "website": "https://techcorp.com",
            "linkedin_url": "https://linkedin.com/company/techcorp",
            "logo_url": "https://techcorp.com/logo.png",
            "tech_stack": ["Python", "Go", "Kubernetes", "AWS", "PostgreSQL", "Redis"],
            "culture_tags": ["Remote-first", "Engineering-driven", "Open source"],
            "benefits": ["Health insurance", "401k matching", "Learning budget", "Flexible PTO"],
            "glassdoor_rating": 4.3,
            "glassdoor_reviews_count": 1250,
            "source_company_id": "mock_comp_1",
            "source_url": "https://example.com/companies/techcorp",
            "quality_score": 0.9,
        },
        {
            "name": "StartupXYZ",
            "domain": "startupxyz.io",
            "description": "Fast-growing startup revolutionizing the fintech space with AI-powered payments.",
            "industry": "Financial Technology",
            "company_size": "51-200",
            "headquarters": "New York, NY",
            "founded_year": 2019,
            "website": "https://startupxyz.io",
            "linkedin_url": "https://linkedin.com/company/startupxyz",
            "logo_url": "https://startupxyz.io/logo.png",
            "tech_stack": ["TypeScript", "React", "Node.js", "MongoDB", "GraphQL", "Docker"],
            "culture_tags": ["Fast-paced", "Ownership", "Transparent"],
            "benefits": ["Equity", "Health insurance", "Remote work", "Team retreats"],
            "glassdoor_rating": 4.5,
            "glassdoor_reviews_count": 85,
            "source_company_id": "mock_comp_2",
            "source_url": "https://example.com/companies/startupxyz",
            "quality_score": 0.85,
        },
        {
            "name": "AI Innovations Inc",
            "domain": "aiinnovations.com",
            "description": "Cutting-edge AI research company developing foundation models for enterprise.",
            "industry": "Technology",
            "company_size": "201-500",
            "headquarters": "Boston, MA",
            "founded_year": 2017,
            "website": "https://aiinnovations.com",
            "linkedin_url": "https://linkedin.com/company/ai-innovations",
            "logo_url": "https://aiinnovations.com/logo.png",
            "tech_stack": ["Python", "PyTorch", "TensorFlow", "Kubernetes", "CUDA", "Ray"],
            "culture_tags": ["Research-focused", "Publication-friendly", "Collaborative"],
            "benefits": ["Health insurance", "Research budget", "Conference travel", "GPU credits"],
            "glassdoor_rating": 4.6,
            "glassdoor_reviews_count": 210,
            "source_company_id": "mock_comp_3",
            "source_url": "https://example.com/companies/aiinnovations",
            "quality_score": 0.95,
        },
        {
            "name": "CloudScale",
            "domain": "cloudscale.io",
            "description": "Infrastructure automation platform helping companies scale their cloud operations.",
            "industry": "Technology",
            "company_size": "11-50",
            "headquarters": "Austin, TX",
            "founded_year": 2020,
            "website": "https://cloudscale.io",
            "linkedin_url": "https://linkedin.com/company/cloudscale",
            "logo_url": "https://cloudscale.io/logo.png",
            "tech_stack": ["Go", "Terraform", "Kubernetes", "AWS", "GCP", "Prometheus"],
            "culture_tags": ["DevOps-first", "Automation", "Blameless postmortems"],
            "benefits": ["Health insurance", "Home office stipend", "On-call rotation", "Learning days"],
            "glassdoor_rating": 4.4,
            "glassdoor_reviews_count": 45,
            "source_company_id": "mock_comp_4",
            "source_url": "https://example.com/companies/cloudscale",
            "quality_score": 0.88,
        },
        {
            "name": "DesignFirst",
            "domain": "designfirst.co",
            "description": "Design-focused product studio creating beautiful, accessible digital experiences.",
            "industry": "Technology",
            "company_size": "11-50",
            "headquarters": "Remote",
            "founded_year": 2018,
            "website": "https://designfirst.co",
            "linkedin_url": "https://linkedin.com/company/designfirst",
            "logo_url": "https://designfirst.co/logo.png",
            "tech_stack": ["Vue.js", "TypeScript", "Tailwind", "Figma", "Storybook", "Jest"],
            "culture_tags": ["Design-led", "Async communication", "Work-life balance"],
            "benefits": ["Health insurance", "Design tools budget", "Flexible hours", "Annual offsite"],
            "glassdoor_rating": 4.7,
            "glassdoor_reviews_count": 62,
            "source_company_id": "mock_comp_5",
            "source_url": "https://example.com/companies/designfirst",
            "quality_score": 0.92,
        },
    ]

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._source_name = "mock_companies"
        self._source_type = "internal_database"
        self._delay = self.config.get("delay", 0.1)
        self._failure_rate = self.config.get("failure_rate", 0.0)
    
    @property
    def source_name(self) -> str:
        return self._source_name
    
    @property
    def source_type(self) -> str:
        return self._source_type

    async def fetch(self, query: str = "", industry: Optional[str] = None, 
                    location: Optional[str] = None, limit: int = 50, **kwargs) -> List[Dict[str, Any]]:
        """Return mock company data for testing."""
        await asyncio.sleep(self._delay)
        
        if self._failure_rate > 0 and random.random() < self._failure_rate:
            raise ConnectionError("Simulated collector failure")
        
        filtered = []
        query_lower = query.lower()
        
        for company in self.MOCK_COMPANIES:
            if query_lower and not (
                query_lower in company["name"].lower() or
                query_lower in company["description"].lower() or
                any(query_lower in t.lower() for t in company["tech_stack"])
            ):
                continue
            
            if industry and industry.lower() not in company["industry"].lower():
                continue
            
            if location and location.lower() not in company["headquarters"].lower():
                continue
            
            filtered.append(company.copy())
            
            if len(filtered) >= limit:
                break
        
        return filtered

    async def parse(self, raw_data: List[Dict[str, Any]]) -> List[RawDataRecord]:
        """Parse raw mock data into RawDataRecord objects."""
        records = []
        for company in raw_data:
            record = RawDataRecord.create(
                source_id="mock_companies",
                source_name="Mock Company Provider",
                source_type="internal_database",
                external_id=company["source_company_id"],
                source_url=company["source_url"],
                raw_payload=company,
                metadata={"mock": True}
            )
            records.append(record)
        return records

    async def health_check(self) -> CollectorHealth:
        """Mock collector is always healthy."""
        return CollectorHealth.HEALTHY