import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


def extract_projects_from_text(text: str) -> list[dict]:
    """Extract project information from text."""
    projects = []

    project_indicators = [
        r"project[:\s]",
        r"built[:\s]",
        r"developed[:\s]",
        r"created[:\s]",
        r"github\.com",
        r"gitlab\.com",
    ]

    lines = text.split("\n")
    current_project = None

    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue

        is_new_project = False
        for indicator in project_indicators:
            if re.search(indicator, line_stripped, re.IGNORECASE):
                is_new_project = True
                break

        if is_new_project and current_project:
            projects.append(current_project)

        if is_new_project:
            current_project = {
                "name": line_stripped[:100],
                "description": line_stripped,
                "technologies": [],
                "url": None,
            }
        elif current_project:
            current_project["description"] += " " + line_stripped

            urls = re.findall(r'https?://[^\s]+', line_stripped)
            if urls:
                current_project["url"] = urls[0]

            tech_matches = re.findall(
                r'\b(python|javascript|typescript|react|vue|angular|node|django|flask|fastapi|postgresql|mongodb|docker|kubernetes|aws|gcp|azure)\b',
                line_stripped,
                re.IGNORECASE,
            )
            for tech in tech_matches:
                if tech.lower() not in [t.lower() for t in current_project["technologies"]]:
                    current_project["technologies"].append(tech)

    if current_project:
        projects.append(current_project)

    return projects


def extract_technologies(text: str) -> list[str]:
    """Extract technology mentions from text."""
    tech_keywords = [
        "python", "javascript", "typescript", "java", "c++", "c#", "go", "rust",
        "react", "vue", "angular", "svelte", "next.js", "nuxt",
        "django", "flask", "fastapi", "spring", "express", "node.js",
        "postgresql", "mysql", "mongodb", "redis", "elasticsearch",
        "docker", "kubernetes", "aws", "gcp", "azure", "terraform",
        "git", "github", "gitlab", "ci/cd", "jenkins",
        "tensorflow", "pytorch", "scikit-learn", "pandas", "numpy",
        "graphql", "rest", "grpc", "kafka", "rabbitmq",
        "html", "css", "sass", "tailwind", "bootstrap",
    ]

    text_lower = text.lower()
    found = []
    for tech in tech_keywords:
        if re.search(rf"\b{re.escape(tech)}\b", text_lower):
            found.append(tech)
    return found


class ProjectAnalyzerAgent:
    """Agent responsible for analyzing and extracting project information."""

    def __init__(self):
        self.name = "project_analyzer_agent"

    async def analyze_projects(self, raw_text: str, sections: dict) -> list[dict]:
        """Extract and analyze projects from resume."""
        logger.info("Analyzing projects from resume")

        projects_text = sections.get("projects", "")
        all_text = raw_text or " ".join(sections.values())

        projects = extract_projects_from_text(projects_text or all_text)
        technologies = extract_technologies(all_text)

        for project in projects:
            if not project.get("technologies"):
                project["technologies"] = extract_technologies(project.get("description", ""))

        return {
            "projects": projects,
            "all_technologies": technologies,
            "project_count": len(projects),
        }