"""
Mock course/learning resource collector for development and testing.
"""

import asyncio
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from backend.data_pipeline.collectors.base_collector import BaseCollector, RawDataRecord, CollectorHealth


class MockCourseCollector(BaseCollector):
    """Mock course/learning resource collector for development/testing."""
    
    MOCK_COURSES = [
        {
            "title": "Machine Learning Specialization",
            "provider": "coursera",
            "provider_name": "Coursera",
            "url": "https://www.coursera.org/specializations/machine-learning-introduction",
            "description": "This Specialization is taught by Andrew Ng and covers the fundamentals of machine learning. Learn about supervised learning, unsupervised learning, and best practices.",
            "skills": ["Machine Learning", "Python", "Supervised Learning", "Unsupervised Learning", "Neural Networks"],
            "technologies": ["Python", "TensorFlow", "Scikit-learn", "Jupyter"],
            "level": "beginner",
            "duration_hours": 60.0,
            "duration_weeks": 12,
            "price": 49.0,
            "currency": "USD",
            "is_free": False,
            "certificate_available": True,
            "language": "en",
            "prerequisites": ["Basic Python programming", "High school mathematics"],
            "learning_outcomes": [
                "Build and train machine learning models",
                "Understand supervised and unsupervised learning",
                "Apply ML to real-world problems",
            ],
            "source_course_id": "course_ml_specialization",
            "source_url": "https://www.coursera.org/specializations/machine-learning-introduction",
            "published_date": (datetime.utcnow() - timedelta(days=365)).isoformat(),
            "retrieved_date": datetime.utcnow().isoformat(),
            "rating": 4.9,
            "review_count": 150000,
            "enrollment_count": 2000000,
            "quality_score": 0.98,
        },
        {
            "title": "Full Stack Web Development with React and Node.js",
            "provider": "udemy",
            "provider_name": "Udemy",
            "url": "https://www.udemy.com/course/fullstack-web-development/",
            "description": "Learn to build complete web applications with React, Node.js, Express, and MongoDB. From frontend to backend to deployment.",
            "skills": ["React", "Node.js", "Express", "MongoDB", "JavaScript", "HTML/CSS"],
            "technologies": ["React", "Node.js", "Express", "MongoDB", "Mongoose", "JWT", "Docker"],
            "level": "intermediate",
            "duration_hours": 45.5,
            "duration_weeks": 8,
            "price": 84.99,
            "currency": "USD",
            "is_free": False,
            "certificate_available": True,
            "language": "en",
            "prerequisites": ["Basic JavaScript knowledge", "HTML/CSS fundamentals"],
            "learning_outcomes": [
                "Build full-stack web applications",
                "Deploy applications to cloud platforms",
                "Implement authentication and authorization",
            ],
            "source_course_id": "course_fullstack_react_node",
            "source_url": "https://www.udemy.com/course/fullstack-web-development/",
            "published_date": (datetime.utcnow() - timedelta(days=180)).isoformat(),
            "retrieved_date": datetime.utcnow().isoformat(),
            "rating": 4.7,
            "review_count": 25000,
            "enrollment_count": 120000,
            "quality_score": 0.92,
        },
        {
            "title": "Kubernetes for Developers",
            "provider": "pluralsight",
            "provider_name": "Pluralsight",
            "url": "https://www.pluralsight.com/courses/kubernetes-developers",
            "description": "Learn to deploy, manage, and scale containerized applications using Kubernetes. Covers pods, services, deployments, and Helm charts.",
            "skills": ["Kubernetes", "Docker", "Container Orchestration", "DevOps", "Cloud Native"],
            "technologies": ["Kubernetes", "Docker", "Helm", "kubectl", "YAML"],
            "level": "intermediate",
            "duration_hours": 12.0,
            "duration_weeks": 4,
            "price": 29.0,
            "currency": "USD",
            "is_free": False,
            "certificate_available": True,
            "language": "en",
            "prerequisites": ["Docker basics", "Linux command line", "YAML syntax"],
            "learning_outcomes": [
                "Deploy applications to Kubernetes clusters",
                "Manage configuration with ConfigMaps and Secrets",
                "Implement CI/CD pipelines for Kubernetes",
            ],
            "source_course_id": "course_kubernetes_devs",
            "source_url": "https://www.pluralsight.com/courses/kubernetes-developers",
            "published_date": (datetime.utcnow() - timedelta(days=90)).isoformat(),
            "retrieved_date": datetime.utcnow().isoformat(),
            "rating": 4.6,
            "review_count": 8500,
            "enrollment_count": 45000,
            "quality_score": 0.9,
        },
        {
            "title": "Python for Everybody - Free Course",
            "provider": "freecodecamp",
            "provider_name": "freeCodeCamp",
            "url": "https://www.freecodecamp.org/learn/scientific-computing-with-python/",
            "description": "Learn Python programming from scratch. Covers variables, loops, functions, data structures, file I/O, and more.",
            "skills": ["Python", "Programming Fundamentals", "Data Structures", "File I/O"],
            "technologies": ["Python", "IDLE", "VS Code"],
            "level": "beginner",
            "duration_hours": 30.0,
            "duration_weeks": 6,
            "price": 0.0,
            "currency": "USD",
            "is_free": True,
            "certificate_available": True,
            "language": "en",
            "prerequisites": ["No prior programming experience required"],
            "learning_outcomes": [
                "Write Python programs to solve problems",
                "Understand core programming concepts",
                "Work with data structures and files",
            ],
            "source_course_id": "course_python_everybody",
            "source_url": "https://www.freecodecamp.org/learn/scientific-computing-with-python/",
            "published_date": (datetime.utcnow() - timedelta(days=730)).isoformat(),
            "retrieved_date": datetime.utcnow().isoformat(),
            "rating": 4.8,
            "review_count": 50000,
            "enrollment_count": 500000,
            "quality_score": 0.95,
        },
        {
            "title": "System Design Interview Preparation",
            "provider": "educative",
            "provider_name": "Educative.io",
            "url": "https://www.educative.io/courses/grokking-the-system-design-interview",
            "description": "Master system design concepts for technical interviews. Covers scalability, databases, caching, load balancing, and real-world architecture patterns.",
            "skills": ["System Design", "Distributed Systems", "Scalability", "Architecture Patterns", "Database Design"],
            "technologies": ["Redis", "MongoDB", "PostgreSQL", "Kafka", "NGINX", "Docker", "Kubernetes"],
            "level": "advanced",
            "duration_hours": 25.0,
            "duration_weeks": 6,
            "price": 79.0,
            "currency": "USD",
            "is_free": False,
            "certificate_available": True,
            "language": "en",
            "prerequisites": ["Software development experience", "Basic networking knowledge", "Database fundamentals"],
            "learning_outcomes": [
                "Design scalable distributed systems",
                "Choose appropriate databases and caching strategies",
                "Handle system design interview questions confidently",
            ],
            "source_course_id": "course_system_design",
            "source_url": "https://www.educative.io/courses/grokking-the-system-design-interview",
            "published_date": (datetime.utcnow() - timedelta(days=120)).isoformat(),
            "retrieved_date": datetime.utcnow().isoformat(),
            "rating": 4.8,
            "review_count": 12000,
            "enrollment_count": 80000,
            "quality_score": 0.94,
        },
    ]

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._source_name = "mock_courses"
        self._source_type = "internal_database"
        self._delay = self.config.get("delay", 0.1)
        self._failure_rate = self.config.get("failure_rate", 0.0)
    
    @property
    def source_name(self) -> str:
        return self._source_name
    
    @property
    def source_type(self) -> str:
        return self._source_type

    async def fetch(self, query: str = "", provider: Optional[str] = None, 
                    level: Optional[str] = None, is_free: Optional[bool] = None,
                    limit: int = 50, **kwargs) -> List[Dict[str, Any]]:
        """Return mock course data for testing."""
        await asyncio.sleep(self._delay)
        
        if self._failure_rate > 0 and random.random() < self._failure_rate:
            raise ConnectionError("Simulated collector failure")
        
        filtered = []
        query_lower = query.lower()
        
        for course in self.MOCK_COURSES:
            if query_lower and not (
                query_lower in course["title"].lower() or
                query_lower in course["description"].lower() or
                any(query_lower in s.lower() for s in course.get("skills", []))
            ):
                continue
            
            if provider and provider != course.get("provider"):
                continue
            
            if level and level != course.get("level"):
                continue
            
            if is_free is not None and is_free != course.get("is_free"):
                continue
            
            filtered.append(course.copy())
            
            if len(filtered) >= limit:
                break
        
        return filtered

    async def parse(self, raw_data: List[Dict[str, Any]]) -> List[RawDataRecord]:
        """Parse raw mock data into RawDataRecord objects."""
        records = []
        for course in raw_data:
            record = RawDataRecord.create(
                source_id="mock_courses",
                source_name="Mock Course Provider",
                source_type="internal_database",
                external_id=course["source_course_id"],
                source_url=course["source_url"],
                raw_payload=course,
                metadata={"mock": True}
            )
            records.append(record)
        return records

    async def health_check(self) -> CollectorHealth:
        """Mock collector is always healthy."""
        return CollectorHealth.HEALTHY