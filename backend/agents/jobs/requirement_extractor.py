import logging
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ExtractedRequirements:
    """Structured job requirements."""
    required_skills: List[Dict[str, Any]]
    preferred_skills: List[Dict[str, Any]]
    experience_years: Optional[int]
    education_level: Optional[str]
    certifications: List[str]
    responsibilities: List[str]
    soft_skills: List[str]
    must_have_keywords: List[str]
    nice_to_have_keywords: List[str]


REQUIRED_PATTERNS = [
    r"(?:required|must have|essential|mandatory)[\s:]+(.+?)(?:\n|$)",
    r"(?:requirements?|qualifications?)[\s:]+(.+?)(?:\n|$)",
    r"(?:you (?:must|should|need to))[^.]*?\.",
]

PREFERRED_PATTERNS = [
    r"(?:preferred|nice to have|desired|bonus|plus)[\s:]+(.+?)(?:\n|$)",
    r"(?:ideal candidate|would be great|a plus)[^.]*?\.",
]

EXPERIENCE_PATTERNS = [
    r"(\d+)\+?\s*years?\s*(?:of\s*)?(?:experience|exp)",
    r"(\d+)[-\s]*(\d+)\s*years?\s*(?:of\s*)?experience",
    r"minimum\s*(?:of\s*)?(\d+)\s*years?",
]

EDUCATION_PATTERNS = [
    r"\b(phd|ph\.d|doctorate)\b",
    r"\b(master'?s?|m\.?s\.?|m\.?a\.?|mba)\b",
    r"\b(bachelor'?s?|b\.?s\.?|b\.?a\.?|b\.?tech|b\.?e\.)\b",
    r"\b(associate'?s?|a\.?s\.?|a\.?a\.)\b",
    r"\b(high school|ged)\b",
]

CERTIFICATION_PATTERNS = [
    r"\b(aws|azure|gcp)\s*(?:certified|certification)\b",
    r"\b(pmp|scrum master|csm|psm)\b",
    r"\b(cissp|security\+|ceh)\b",
    r"\b(ckad|cka|ckad)\b",
    r"\b(terraform|kubernetes)\s*(?:certified|associate)\b",
]

SOFT_SKILLS = [
    "communication", "leadership", "teamwork", "collaboration",
    "problem solving", "critical thinking", "adaptability",
    "time management", "project management", "mentoring",
    "creativity", "analytical", "detail oriented", "organized",
    "self-motivated", "proactive", "customer focused",
]


def extract_required_skills(text: str) -> List[Dict[str, Any]]:
    """Extract required skills from job text."""
    skills = []
    text_lower = text.lower()

    tech_skills = [
        "python", "javascript", "typescript", "java", "c++", "c#", "go", "rust",
        "react", "vue", "angular", "svelte", "next.js", "nuxt", "django", "flask",
        "fastapi", "spring", "express", "node.js", "deno", "bun",
        "postgresql", "mysql", "mongodb", "redis", "elasticsearch", "sqlite",
        "docker", "kubernetes", "aws", "gcp", "azure", "terraform", "ansible",
        "git", "github", "gitlab", "ci/cd", "jenkins", "github actions",
        "machine learning", "deep learning", "tensorflow", "pytorch", "scikit-learn",
        "pandas", "numpy", "sql", "nosql", "graphql", "rest", "grpc",
        "microservices", "serverless", "kafka", "rabbitmq", "message queue",
        "linux", "bash", "vim", "vscode", "intellij",
        "agile", "scrum", "kanban", "jira", "confluence",
        "html", "css", "sass", "tailwind", "bootstrap",
        "testing", "jest", "pytest", "cypress", "playwright",
    ]

    for skill in tech_skills:
        pattern = rf"\b{re.escape(skill)}\b"
        matches = list(re.finditer(pattern, text_lower))
        if matches:
            # Check if in required section
            is_required = False
            for match in matches:
                start = max(0, match.start() - 100)
                context = text_lower[start:match.end() + 50]
                if any(word in context for word in ["required", "must have", "essential", "mandatory", "requirement"]):
                    is_required = True
                    break

            skills.append({
                "name": skill,
                "required": is_required,
                "category": "technical",
                "mentions": len(matches),
            })

    return skills


def extract_experience_years(text: str) -> Optional[int]:
    """Extract years of experience required."""
    text_lower = text.lower()
    max_years = 0

    for pattern in EXPERIENCE_PATTERNS:
        matches = re.findall(pattern, text_lower)
        for match in matches:
            if isinstance(match, tuple):
                years = max(int(m) for m in match if m.isdigit())
            else:
                years = int(match)
            max_years = max(max_years, years)

    return max_years if max_years > 0 else None


def extract_education_level(text: str) -> Optional[str]:
    """Extract minimum education level required."""
    text_lower = text.lower()
    levels = []

    for pattern in EDUCATION_PATTERNS:
        if re.search(pattern, text_lower):
            if "phd" in pattern or "doctorate" in pattern:
                levels.append("phd")
            elif "master" in pattern or "mba" in pattern:
                levels.append("masters")
            elif "bachelor" in pattern:
                levels.append("bachelors")
            elif "associate" in pattern:
                levels.append("associates")
            elif "high school" in pattern or "ged" in pattern:
                levels.append("high_school")

    if not levels:
        return None

    # Return highest level
    hierarchy = {"high_school": 1, "associates": 2, "bachelors": 3, "masters": 4, "phd": 5}
    return max(levels, key=lambda x: hierarchy.get(x, 0))


def extract_certifications(text: str) -> List[str]:
    """Extract required certifications."""
    text_lower = text.lower()
    certs = []

    for pattern in CERTIFICATION_PATTERNS:
        matches = re.findall(pattern, text_lower)
        certs.extend(matches)

    return list(set(certs))


def extract_soft_skills(text: str) -> List[str]:
    """Extract soft skills from job text."""
    text_lower = text.lower()
    found = []

    for skill in SOFT_SKILLS:
        if re.search(rf"\b{re.escape(skill)}\b", text_lower):
            found.append(skill)

    return found


def extract_responsibilities(text: str) -> List[str]:
    """Extract key responsibilities."""
    responsibilities = []

    # Look for bullet points
    bullet_patterns = [
        r"[*\-\*]\s*(.+?)(?:\n|$)",
        r"\d+\.\s*(.+?)(?:\n|$)",
    ]

    for pattern in bullet_patterns:
        matches = re.findall(pattern, text)
        responsibilities.extend([m.strip() for m in matches if len(m.strip()) > 10])

    # Also look for responsibility sections
    resp_sections = re.findall(
        r"(?:responsibilities|duties|what you['']?ll do)[\s:]+(.+?)(?:\n\n|\n[A-Z]|$)",
        text, re.IGNORECASE | re.DOTALL
    )
    for section in resp_sections:
        bullets = re.findall(r"[*\-\*]\s*(.+?)(?:\n|$)", section)
        responsibilities.extend([b.strip() for b in bullets if len(b.strip()) > 10])

    return list(set(responsibilities))[:15]  # Limit to top 15


def extract_keywords(text: str, required: bool = True) -> List[str]:
    """Extract must-have or nice-to-have keywords."""
    text_lower = text.lower()
    keywords = []

    patterns = REQUIRED_PATTERNS if required else PREFERRED_PATTERNS

    for pattern in patterns:
        matches = re.findall(pattern, text_lower, re.IGNORECASE | re.DOTALL)
        for match in matches:
            # Split by common delimiters
            items = re.split(r"[,\n;*\-\*]| and | or ", match)
            for item in items:
                item = item.strip().rstrip(".")
                if 3 < len(item) < 100:
                    keywords.append(item)

    return list(set(keywords))[:20]


class RequirementExtractor:
    """Extract structured requirements from job descriptions."""

    def __init__(self):
        self.name = "requirement_extractor"

    def extract(self, job) -> ExtractedRequirements:
        """Extract requirements from a normalized job."""
        logger.info(f"Extracting requirements for: {job.title}")

        # Combine all text fields
        full_text = " ".join(filter(None, [
            job.description,
            job.requirements,
            job.responsibilities,
        ]))

        required_skills = extract_required_skills(full_text)
        preferred_skills = [s for s in required_skills if not s["required"]]
        required_skills = [s for s in required_skills if s["required"]]

        experience_years = extract_experience_years(full_text)
        education_level = extract_education_level(full_text)
        certifications = extract_certifications(full_text)
        responsibilities = extract_responsibilities(full_text)
        soft_skills = extract_soft_skills(full_text)
        must_have = extract_keywords(full_text, required=True)
        nice_to_have = extract_keywords(full_text, required=False)

        return ExtractedRequirements(
            required_skills=required_skills,
            preferred_skills=preferred_skills,
            experience_years=experience_years,
            education_level=education_level,
            certifications=certifications,
            responsibilities=responsibilities,
            soft_skills=soft_skills,
            must_have_keywords=must_have,
            nice_to_have_keywords=nice_to_have,
        )

    def extract_batch(self, jobs: List) -> List[ExtractedRequirements]:
        """Extract requirements for multiple jobs."""
        return [self.extract(job) for job in jobs]