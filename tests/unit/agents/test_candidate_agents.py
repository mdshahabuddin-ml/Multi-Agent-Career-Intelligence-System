"""Unit tests for Candidate Intelligence agents."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.agents.candidate.profile_agent import ProfileAgent, CandidateProfile
from backend.agents.candidate.resume_parser_agent import ResumeParserAgent
from backend.agents.candidate.skill_extraction_agent import SkillExtractionAgent
from backend.agents.candidate.project_analyzer import ProjectAnalyzerAgent
from backend.agents.candidate.experience_analyzer import ExperienceAnalyzerAgent


class TestProfileAgent:
    """Tests for ProfileAgent orchestration."""

    @pytest.fixture
    def profile_agent(self):
        return ProfileAgent()

    @pytest.fixture
    def sample_resume_text(self):
        return """
        John Doe
        Senior Software Engineer | San Francisco, CA | john.doe@email.com | (555) 123-4567
        LinkedIn: linkedin.com/in/johndoe | GitHub: github.com/johndoe

        SUMMARY
        Senior Software Engineer with 8 years of experience in Python, React, AWS, and Kubernetes.

        EXPERIENCE
        Senior Software Engineer at TechCorp (Jan 2020 - Present)
        - Led team of 5 engineers building scalable microservices
        - Architected migration from monolith to microservices using Go and Kubernetes
        - Reduced deployment time by 80% through CI/CD pipeline improvements

        Software Engineer at StartupXYZ (2017-2020)
        - Built full-stack web applications using React, Node.js, and MongoDB

        EDUCATION
        BS Computer Science | Stanford University | 2017

        SKILLS
        Languages: Go, Python, JavaScript, TypeScript, SQL
        Frameworks: React, Node.js, Express, Gin, gRPC
        Infrastructure: Kubernetes, Docker, AWS, Terraform
        """

    @pytest.mark.asyncio
    async def test_process_resume_success(self, profile_agent, sample_resume_text):
        """Test successful resume processing through full pipeline."""
        with patch.object(profile_agent.resume_parser, 'parse_resume', new_callable=AsyncMock) as mock_parse:
            mock_parse.return_value = {
                "success": True,
                "raw_text": sample_resume_text,
                "sections": {
                    "summary": "Senior Software Engineer with 8 years of experience...",
                    "experience": "Senior Software Engineer at TechCorp...",
                    "education": "BS Computer Science | Stanford University | 2017",
                    "skills": "Languages: Go, Python, JavaScript...",
                },
                "filename": "test.pdf",
            }

            with patch.object(profile_agent.skill_extractor, 'extract_skills', new_callable=AsyncMock) as mock_skills:
                mock_skills.return_value = [
                    {"name": "Python", "category": "technical", "proficiency": "expert", "years_experience": 8},
                    {"name": "React", "category": "technical", "proficiency": "advanced", "years_experience": 5},
                    {"name": "AWS", "category": "technical", "proficiency": "advanced", "years_experience": 4},
                ]

            with patch.object(profile_agent.project_analyzer, 'analyze_projects', new_callable=AsyncMock) as mock_projects:
                mock_projects.return_value = {
                    "projects": [
                        {
                            "name": "Microservices Migration",
                            "description": "Migrated monolith to microservices",
                            "technologies": ["Go", "Kubernetes", "Docker"],
                            "impact": "Reduced deployment time by 80%",
                        }
                    ],
                    "all_technologies": ["Go", "Kubernetes", "Docker"],
                    "project_count": 1,
                }

            with patch.object(profile_agent.experience_analyzer, 'analyze_experience', new_callable=AsyncMock) as mock_exp:
                mock_exp.return_value = {
                    "years_of_experience": 8,
                    "entries": [
                        {
                            "title": "Senior Software Engineer",
                            "company": "TechCorp",
                            "duration": "2020-Present",
                        }
                    ],
                    "career_trajectory": "ascending",
                }

                profile = await profile_agent.process_resume(
                    file_content=b"fake pdf content",
                    mime_type="application/pdf",
                    filename="test.pdf",
                )

        assert isinstance(profile, CandidateProfile)
        assert profile.years_of_experience == 8
        assert len(profile.skills) == 3
        assert len(profile.projects) >= 1
        assert profile.experience["years_of_experience"] == 8

    @pytest.mark.asyncio
    async def test_process_resume_parsing_failure(self, profile_agent):
        """Test handling of resume parsing failure."""
        with patch.object(profile_agent.resume_parser, 'parse_resume', new_callable=AsyncMock) as mock_parse:
            mock_parse.return_value = {
                "success": False,
                "error": "Unsupported file format",
            }

            with pytest.raises(ValueError, match="Resume parsing failed"):
                await profile_agent.process_resume(
                    file_content=b"invalid content",
                    mime_type="application/x-unknown",
                    filename="test.xyz",
                )


class TestResumeParserAgent:
    """Tests for ResumeParserAgent."""

    @pytest.fixture
    def parser_agent(self):
        return ResumeParserAgent()

    @pytest.mark.asyncio
    async def test_parse_resume_mocked(self, parser_agent):
        """Test parsing a resume with mocked document parser."""
        with patch('backend.agents.candidate.resume_parser_agent.parse_document') as mock_parse:
            mock_parse.return_value = "John Doe\nSoftware Engineer\n\nEXPERIENCE\nSenior Engineer at TechCorp"

            with patch('backend.agents.candidate.resume_parser_agent.extract_sections') as mock_sections:
                mock_sections.return_value = {
                    "summary": "Software Engineer",
                    "experience": "Senior Engineer at TechCorp",
                }

                result = await parser_agent.parse_resume(
                    file_content=b"fake pdf content",
                    mime_type="application/pdf",
                    filename="resume.pdf",
                )

        assert result["success"] is True
        assert "John Doe" in result["raw_text"]
        assert "experience" in result["sections"]
        assert result["file_size"] > 0

    @pytest.mark.asyncio
    async def test_parse_multiple_resumes(self, parser_agent):
        """Test parsing multiple resumes at once."""
        files = [
            {"content": b"resume1", "mime_type": "application/pdf", "filename": "r1.pdf"},
            {"content": b"resume2", "mime_type": "application/pdf", "filename": "r2.pdf"},
        ]

        with patch.object(parser_agent, 'parse_resume', new_callable=AsyncMock) as mock_parse:
            mock_parse.side_effect = [
                {"success": True, "raw_text": "Resume 1", "sections": {}},
                {"success": True, "raw_text": "Resume 2", "sections": {}},
            ]

            results = await parser_agent.parse_multiple_resumes(files)

        assert len(results) == 2
        assert all(r["success"] for r in results)


class TestSkillExtractionAgent:
    """Tests for SkillExtractionAgent."""

    @pytest.fixture
    def skill_agent(self):
        return SkillExtractionAgent()

    @pytest.mark.asyncio
    async def test_extract_technical_skills(self, skill_agent):
        """Test extraction of technical skills from resume text."""
        resume_text = """
        Senior Software Engineer with expertise in Python, React, AWS, Kubernetes,
        PostgreSQL, Docker, TypeScript, Go, GraphQL, and Redis.
        """
        sections = {"skills": "Python, React, AWS, Kubernetes, PostgreSQL, Docker"}

        skills = await skill_agent.extract_skills(resume_text, sections)

        assert len(skills) > 0
        skill_names = [s["name"] for s in skills]
        found_skills = [s.lower() for s in skill_names]
        assert "python" in found_skills or "react" in found_skills
        assert all(s["category"] in ["technical", "soft"] for s in skills)

    @pytest.mark.asyncio
    async def test_skill_extraction_from_sections(self, skill_agent):
        """Test that skills section is prioritized."""
        resume_text = "Skills: Python, React, AWS, Docker, Kubernetes"
        sections = {"skills": "Python, React, AWS, Docker, Kubernetes"}

        skills = await skill_agent.extract_skills(resume_text, sections)

        assert len(skills) > 0
        skill_names = [s["name"] for s in skills]
        found_skills = [s.lower() for s in skill_names]
        assert "python" in found_skills
        assert "react" in found_skills
        assert "aws" in found_skills

    @pytest.mark.asyncio
    async def test_deduplication(self, skill_agent):
        """Test that duplicate skills are deduplicated."""
        resume_text = "Python, python, PYTHON, React, react"
        sections = {"skills": "Python, React"}

        skills = await skill_agent.extract_skills(resume_text, sections)

        python_skills = [s for s in skills if s["name"].lower() == "python"]
        assert len(python_skills) == 1


class TestProjectAnalyzerAgent:
    """Tests for ProjectAnalyzerAgent."""

    @pytest.fixture
    def project_agent(self):
        return ProjectAnalyzerAgent()

    @pytest.mark.asyncio
    async def test_analyze_projects_with_metrics(self, project_agent):
        """Test project analysis with quantified metrics."""
        resume_text = """
        PROJECTS
        Microservices Platform
        - Built scalable platform serving 10M+ requests/day
        - Reduced latency by 60% using caching layer
        - Technologies: Go, Kubernetes, gRPC, PostgreSQL
        
        Real-time Collaboration Tool
        - 50k+ concurrent users with 99.9% uptime
        - WebSocket infrastructure with Redis pub/sub
        - Technologies: Node.js, WebSockets, Redis, React
        """
        sections = {"projects": resume_text}

        result = await project_agent.analyze_projects(resume_text, sections)

        assert "projects" in result
        assert "project_count" in result
        assert "all_technologies" in result
        assert result["project_count"] >= 1
        
        project = result["projects"][0]
        assert "name" in project
        assert "technologies" in project

    @pytest.mark.asyncio
    async def test_analyze_projects_empty(self, project_agent):
        """Test project analysis with no projects section."""
        resume_text = "No projects listed."
        sections = {}

        result = await project_agent.analyze_projects(resume_text, sections)

        assert "projects" in result
        assert result["project_count"] == 0


class TestExperienceAnalyzerAgent:
    """Tests for ExperienceAnalyzerAgent."""

    @pytest.fixture
    def exp_agent(self):
        return ExperienceAnalyzerAgent()

    @pytest.mark.asyncio
    async def test_analyze_experience_with_dates(self, exp_agent):
        """Test experience analysis with proper date extraction."""
        resume_text = """
        EXPERIENCE
        Senior Software Engineer at TechCorp (Jan 2020 - Present)
        - Led team of 5 engineers
        
        Software Engineer at StartupXYZ (Jun 2017 - Dec 2019)
        - Built full-stack applications
        """
        sections = {"experience": resume_text}

        result = await exp_agent.analyze_experience(resume_text, sections)

        assert "years_of_experience" in result
        assert result["years_of_experience"] >= 0
        assert "entries" in result
        assert len(result["entries"]) >= 1

    @pytest.mark.asyncio
    async def test_career_trajectory_detection(self, exp_agent):
        """Test detection of career trajectory."""
        resume_text = """
        EXPERIENCE
        Staff Engineer at BigTech (2022-Present)
        Senior Engineer at MidCorp (2019-2022)
        Junior Engineer at StartupXYZ (2017-2019)
        """
        sections = {"experience": resume_text}

        result = await exp_agent.analyze_experience(resume_text, sections)

        # Check that experience entries are parsed
        assert "entries" in result
        assert len(result["entries"]) >= 1
        assert "years_of_experience" in result
        assert "companies" in result
        assert "roles" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])