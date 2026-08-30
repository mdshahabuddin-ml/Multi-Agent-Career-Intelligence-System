"""
Mock skill/technology collector for development and testing.
"""

import asyncio
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from backend.data_pipeline.collectors.base_collector import BaseCollector, RawDataRecord, CollectorHealth


class MockSkillCollector(BaseCollector):
    """Mock skill/technology collector for development/testing."""
    
    MOCK_SKILLS = [
        {
            "name": "Python",
            "category": "programming",
            "description": "High-level, interpreted programming language known for readability and versatility.",
            "aliases": ["py"],
            "is_technology": True,
            "popularity_score": 0.95,
            "market_demand": 0.9,
            "source_skill_id": "skill_python",
            "source_url": "https://www.python.org/",
            "quality_score": 0.98,
        },
        {
            "name": "JavaScript",
            "category": "programming",
            "description": "Dynamic programming language for web development.",
            "aliases": ["js", "ecmascript"],
            "is_technology": True,
            "popularity_score": 0.98,
            "market_demand": 0.95,
            "source_skill_id": "skill_javascript",
            "source_url": "https://developer.mozilla.org/en-US/docs/Web/JavaScript",
            "quality_score": 0.97,
        },
        {
            "name": "TypeScript",
            "category": "programming",
            "description": "Typed superset of JavaScript that compiles to plain JavaScript.",
            "aliases": ["ts"],
            "is_technology": True,
            "popularity_score": 0.85,
            "market_demand": 0.9,
            "source_skill_id": "skill_typescript",
            "source_url": "https://www.typescriptlang.org/",
            "quality_score": 0.95,
        },
        {
            "name": "React",
            "category": "frontend",
            "description": "JavaScript library for building user interfaces.",
            "aliases": ["reactjs", "react.js"],
            "is_technology": True,
            "popularity_score": 0.9,
            "market_demand": 0.92,
            "source_skill_id": "skill_react",
            "source_url": "https://react.dev/",
            "quality_score": 0.96,
        },
        {
            "name": "Kubernetes",
            "category": "devops",
            "description": "Open-source container orchestration platform.",
            "aliases": ["k8s", "kube"],
            "is_technology": True,
            "popularity_score": 0.88,
            "market_demand": 0.85,
            "source_skill_id": "skill_kubernetes",
            "source_url": "https://kubernetes.io/",
            "quality_score": 0.94,
        },
        {
            "name": "PostgreSQL",
            "category": "database",
            "description": "Advanced open-source relational database.",
            "aliases": ["postgres", "psql"],
            "is_technology": True,
            "popularity_score": 0.85,
            "market_demand": 0.8,
            "source_skill_id": "skill_postgresql",
            "source_url": "https://www.postgresql.org/",
            "quality_score": 0.93,
        },
        {
            "name": "AWS",
            "category": "cloud",
            "description": "Amazon Web Services cloud computing platform.",
            "aliases": ["amazon web services"],
            "is_technology": True,
            "popularity_score": 0.92,
            "market_demand": 0.88,
            "source_skill_id": "skill_aws",
            "source_url": "https://aws.amazon.com/",
            "quality_score": 0.95,
        },
        {
            "name": "Machine Learning",
            "category": "ai_ml",
            "description": "Field of AI focused on algorithms that learn from data.",
            "aliases": ["ml", "machinelearning"],
            "is_technology": True,
            "popularity_score": 0.9,
            "market_demand": 0.85,
            "source_skill_id": "skill_machine_learning",
            "source_url": "https://en.wikipedia.org/wiki/Machine_learning",
            "quality_score": 0.9,
        },
        {
            "name": "TensorFlow",
            "category": "ai_ml",
            "description": "Open-source ML framework by Google.",
            "aliases": ["tf"],
            "is_technology": True,
            "popularity_score": 0.75,
            "market_demand": 0.7,
            "source_skill_id": "skill_tensorflow",
            "source_url": "https://www.tensorflow.org/",
            "quality_score": 0.88,
        },
        {
            "name": "Docker",
            "category": "devops",
            "description": "Platform for containerizing applications.",
            "aliases": ["container"],
            "is_technology": True,
            "popularity_score": 0.9,
            "market_demand": 0.88,
            "source_skill_id": "skill_docker",
            "source_url": "https://www.docker.com/",
            "quality_score": 0.96,
        },
        {
            "name": "Communication",
            "category": "soft_skills",
            "description": "Ability to convey information effectively.",
            "aliases": [],
            "is_technology": False,
            "popularity_score": 1.0,
            "market_demand": 1.0,
            "source_skill_id": "skill_communication",
            "source_url": "",
            "quality_score": 0.9,
        },
        {
            "name": "Problem Solving",
            "category": "soft_skills",
            "description": "Ability to analyze and solve complex problems.",
            "aliases": [],
            "is_technology": False,
            "popularity_score": 1.0,
            "market_demand": 1.0,
            "source_skill_id": "skill_problem_solving",
            "source_url": "",
            "quality_score": 0.9,
        },
        {
            "name": "System Design",
            "category": "architecture",
            "description": "Process of defining architecture, components, and interfaces of a system.",
            "aliases": ["architecture", "distributed systems"],
            "is_technology": False,
            "popularity_score": 0.8,
            "market_demand": 0.85,
            "source_skill_id": "skill_system_design",
            "source_url": "",
            "quality_score": 0.88,
        },
    ]

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._source_name = "mock_skills"
        self._source_type = "internal_database"
        self._delay = self.config.get("delay", 0.1)
        self._failure_rate = self.config.get("failure_rate", 0.0)
    
    @property
    def source_name(self) -> str:
        return self._source_name
    
    @property
    def source_type(self) -> str:
        return self._source_type

    async def fetch(self, query: str = "", category: Optional[str] = None, 
                    is_technology: Optional[bool] = None, limit: int = 50, **kwargs) -> List[Dict[str, Any]]:
        """Return mock skill data for testing."""
        await asyncio.sleep(self._delay)
        
        if self._failure_rate > 0 and random.random() < self._failure_rate:
            raise ConnectionError("Simulated collector failure")
        
        filtered = []
        query_lower = query.lower()
        
        for skill in self.MOCK_SKILLS:
            if query_lower and not (
                query_lower in skill["name"].lower() or
                query_lower in skill["description"].lower() or
                any(query_lower in a.lower() for a in skill.get("aliases", []))
            ):
                continue
            
            if category and category != skill.get("category"):
                continue
            
            if is_technology is not None and is_technology != skill.get("is_technology"):
                continue
            
            filtered.append(skill.copy())
            
            if len(filtered) >= limit:
                break
        
        return filtered

    async def parse(self, raw_data: List[Dict[str, Any]]) -> List[RawDataRecord]:
        """Parse raw mock data into RawDataRecord objects."""
        records = []
        for skill in raw_data:
            record = RawDataRecord.create(
                source_id="mock_skills",
                source_name="Mock Skill Provider",
                source_type="internal_database",
                external_id=skill["source_skill_id"],
                source_url=skill["source_url"],
                raw_payload=skill,
                metadata={"mock": True}
            )
            records.append(record)
        return records

    async def health_check(self) -> CollectorHealth:
        """Mock collector is always healthy."""
        return CollectorHealth.HEALTHY