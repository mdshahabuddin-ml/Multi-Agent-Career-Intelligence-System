import logging
from typing import Optional

from backend.agents.candidate.resume_parser_agent import ResumeParserAgent
from backend.agents.candidate.skill_extraction_agent import SkillExtractionAgent
from backend.agents.candidate.project_analyzer import ProjectAnalyzerAgent
from backend.agents.candidate.experience_analyzer import ExperienceAnalyzerAgent

logger = logging.getLogger(__name__)


class CandidateProfile:
    """Structured candidate profile output."""

    def __init__(
        self,
        raw_text: str = "",
        sections: dict = None,
        skills: list[dict] = None,
        projects: list[dict] = None,
        experience: dict = None,
        education: list[dict] = None,
        certifications: list[dict] = None,
        years_of_experience: int = 0,
        target_role: str = "",
        location: str = "",
        summary: str = "",
    ):
        self.raw_text = raw_text
        self.sections = sections or {}
        self.skills = skills or []
        self.projects = projects or []
        self.experience = experience or {}
        self.education = education or []
        self.certifications = certifications or []
        self.years_of_experience = years_of_experience
        self.target_role = target_role
        self.location = location
        self.summary = summary

    def to_dict(self) -> dict:
        return {
            "raw_text": self.raw_text,
            "sections": self.sections,
            "skills": self.skills,
            "projects": self.projects,
            "experience": self.experience,
            "education": self.education,
            "certifications": self.certifications,
            "years_of_experience": self.years_of_experience,
            "target_role": self.target_role,
            "location": self.location,
            "summary": self.summary,
        }


class ProfileAgent:
    """Main agent that orchestrates candidate intelligence pipeline."""

    def __init__(self):
        self.name = "profile_agent"
        self.resume_parser = ResumeParserAgent()
        self.skill_extractor = SkillExtractionAgent()
        self.project_analyzer = ProjectAnalyzerAgent()
        self.experience_analyzer = ExperienceAnalyzerAgent()

    async def process_resume(
        self,
        file_content: bytes,
        mime_type: str,
        filename: str,
    ) -> CandidateProfile:
        """
        Process a resume through the full candidate intelligence pipeline.

        Returns:
            CandidateProfile with all extracted information
        """
        logger.info(f"Processing resume: {filename}")

        parse_result = await self.resume_parser.parse_resume(
            file_content, mime_type, filename
        )

        if not parse_result["success"]:
            raise ValueError(f"Resume parsing failed: {parse_result['error']}")

        raw_text = parse_result["raw_text"]
        sections = parse_result["sections"]

        skills = await self.skill_extractor.extract_skills(raw_text, sections)
        project_analysis = await self.project_analyzer.analyze_projects(raw_text, sections)
        experience_analysis = await self.experience_analyzer.analyze_experience(raw_text, sections)

        profile = CandidateProfile(
            raw_text=raw_text,
            sections=sections,
            skills=skills,
            projects=project_analysis.get("projects", []),
            experience=experience_analysis,
            years_of_experience=experience_analysis.get("years_of_experience", 0),
            summary=sections.get("summary", ""),
        )

        return profile

    async def process_resume_to_dict(
        self,
        file_content: bytes,
        mime_type: str,
        filename: str,
    ) -> dict:
        """Process resume and return dictionary."""
        profile = await self.process_resume(file_content, mime_type, filename)
        return profile.to_dict()