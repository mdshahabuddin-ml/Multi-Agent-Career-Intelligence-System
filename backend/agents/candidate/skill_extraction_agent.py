import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


COMMON_TECH_SKILLS = [
    "python", "javascript", "typescript", "java", "c++", "c#", "go", "rust",
    "react", "vue", "angular", "svelte", "next.js", "nuxt", "django", "flask",
    "fastapi", "spring", "express", "node.js", "deno", "bun",
    "postgresql", "mysql", "mongodb", "redis", "elasticsearch", "sqlite",
    "docker", "kubernetes", "aws", "gcp", "azure", "terraform", "ansible",
    "git", "github", "gitlab", "ci/cd", "jenkins", "github actions",
    "machine learning", "deep learning", "tensorflow", "pytorch", "scikit-learn",
    "pandas", "numpy", "sql", "nosql", "graphql", "rest", "grpc",
    "microservices", "serverless", "event-driven", "message queues",
    "kafka", "rabbitmq", "redis", "celery", "airflow",
    "linux", "bash", "vim", "vscode", "intellij",
    "agile", "scrum", "kanban", "jira", "confluence",
    "html", "css", "sass", "tailwind", "bootstrap",
    "testing", "jest", "pytest", "cypress", "playwright",
    "design patterns", "clean code", "solid", "tdd", "bdd",
]


COMMON_SOFT_SKILLS = [
    "communication", "leadership", "teamwork", "problem solving",
    "critical thinking", "adaptability", "time management",
    "project management", "mentoring", "collaboration",
]


def extract_skills_from_text(text: str, skill_keywords: Optional[list[str]] = None) -> list[dict]:
    """Extract skills from text using keyword matching."""
    if skill_keywords is None:
        skill_keywords = COMMON_TECH_SKILLS + COMMON_SOFT_SKILLS

    text_lower = text.lower()
    found_skills = []

    for skill in skill_keywords:
        pattern = rf"\b{re.escape(skill)}\b"
        if re.search(pattern, text_lower, re.IGNORECASE):
            category = "technical" if skill in COMMON_TECH_SKILLS else "soft"
            found_skills.append({
                "name": skill,
                "category": category,
                "confidence": 0.8,
            })

    return found_skills


def extract_skills_from_sections(sections: dict) -> list[dict]:
    """Extract skills prioritizing the skills section."""
    skills_text = sections.get("skills", "")
    all_text = " ".join(sections.values())

    skills = extract_skills_from_text(skills_text)
    all_skills = extract_skills_from_text(all_text)

    seen = set()
    merged = []
    for skill in skills + all_skills:
        key = skill["name"].lower()
        if key not in seen:
            seen.add(key)
            merged.append(skill)

    return merged


class SkillExtractionAgent:
    """Agent responsible for extracting skills from resume text."""

    def __init__(self, custom_skills: Optional[list[str]] = None):
        self.name = "skill_extraction_agent"
        self.custom_skills = custom_skills or []

    async def extract_skills(self, raw_text: str, sections: dict) -> list[dict]:
        """Extract skills from resume text and sections."""
        logger.info("Extracting skills from resume")

        all_keywords = COMMON_TECH_SKILLS + COMMON_SOFT_SKILLS + self.custom_skills
        skills = extract_skills_from_sections(sections)

        for skill in skills:
            skill["source"] = "resume"

        return skills

    async def extract_skills_from_job_description(self, job_text: str) -> list[dict]:
        """Extract required skills from job description."""
        logger.info("Extracting skills from job description")
        return extract_skills_from_text(job_text)