"""Unit tests for Application Intelligence agents."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from backend.agents.application.ats_resume_agent import ATSResumeAgent, ATSAnalysisResult, ATSIssue, ATSIssueType, ATSIssueSeverity
from backend.agents.application.resume_reviewer import ResumeReviewerAgent, ResumeReviewResult, ReviewIssue, ReviewCategory, IssueSeverity
from backend.agents.application.cover_letter_agent import CoverLetterAgent, CoverLetterContext, CoverLetterResult, CoverLetterTone, CoverLetterLength
from backend.agents.application.application_answer_agent import ApplicationAnswerAgent, ApplicationAnswersResult, AnswerDraft, ApplicationQuestion, QuestionType, AnswerStrategy
from backend.agents.application.application_agent import ApplicationAgent, ApplicationWorkflowResult, ApplicationStatus


class TestATSResumeAgent:
    """Tests for ATSResumeAgent."""

    @pytest.fixture
    def agent(self):
        return ATSResumeAgent()

    @pytest.fixture
    def sample_resume(self):
        return """
        John Doe
        john.doe@email.com | (555) 123-4567 | San Francisco, CA
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

    def test_analyze_strong_resume(self, agent, sample_resume):
        """Test ATS analysis of a strong resume."""
        result = agent.analyze(
            resume_text=sample_resume,
            target_role="software engineer",
        )

        assert isinstance(result, ATSAnalysisResult)
        assert result.overall_score >= 70  # Should pass
        assert result.passed is True
        assert result.keyword_match_score >= 50
        assert len(result.recommendations) > 0

    def test_analyze_resume_missing_contact(self, agent):
        """Test ATS flags missing contact info."""
        resume = """
        John Doe
        Senior Software Engineer
        
        EXPERIENCE
        Software Engineer at TechCorp (2020-Present)
        - Built things
        
        SKILLS
        Python, React
        """
        result = agent.analyze(resume_text=resume, target_role="software engineer")

        contact_issues = [i for i in result.issues if i.type == ATSIssueType.CONTACT_INFO]
        assert len(contact_issues) > 0
        # Should flag missing email, phone, LinkedIn
        issue_titles = [i.title for i in contact_issues]
        assert any("email" in t.lower() for t in issue_titles)

    def test_analyze_resume_missing_sections(self, agent):
        """Test ATS flags missing standard sections."""
        resume = """
        John Doe
        john.doe@email.com
        
        I am a software engineer with 5 years experience.
        I know Python and React.
        """
        result = agent.analyze(resume_text=resume, target_role="software engineer")

        section_issues = [i for i in result.issues if i.type == ATSIssueType.SECTIONS]
        assert len(section_issues) > 0

    def test_analyze_resume_keyword_matching(self, agent, sample_resume):
        """Test keyword matching against target role."""
        result = agent.analyze(
            resume_text=sample_resume,
            target_role="software engineer",
        )

        # Should match common software engineer keywords
        matched = result.matched_keywords
        assert "Python" in matched
        assert "React" in matched
        assert "AWS" in matched

    def test_analyze_resume_length_check(self, agent):
        """Test resume length validation."""
        # Too short
        short_resume = "John Doe\nEngineer\nPython\n"
        result = agent.analyze(resume_text=short_resume)
        length_issues = [i for i in result.issues if i.type == ATSIssueType.LENGTH]
        assert any("too short" in i.title.lower() for i in length_issues)

        # Too long
        long_resume = "John Doe\n" + "Experience\n" * 500
        result = agent.analyze(resume_text=long_resume)
        length_issues = [i for i in result.issues if i.type == ATSIssueType.LENGTH]
        assert any("too long" in i.title.lower() for i in length_issues)

    def test_analyze_with_job_description(self, agent, sample_resume):
        """Test analysis with job description keywords."""
        jd = "We need Python, React, AWS, Kubernetes, Docker, CI/CD, Terraform experience."
        result = agent.analyze(
            resume_text=sample_resume,
            target_role="software engineer",
            job_description=jd,
        )

        # Should have higher keyword match with JD
        assert result.keyword_match_score >= 60


class TestResumeReviewerAgent:
    """Tests for ResumeReviewerAgent."""

    @pytest.fixture
    def agent(self):
        return ResumeReviewerAgent()

    @pytest.fixture
    def strong_resume(self):
        return """
        John Doe
        john.doe@email.com | (555) 123-4567 | San Francisco, CA
        LinkedIn: linkedin.com/in/johndoe | GitHub: github.com/johndoe

        SUMMARY
        Senior Software Engineer with 8 years of experience building scalable systems using Python, React, and AWS. 
        Led teams of 5+ engineers, reduced deployment time by 80%, architected microservices migration.

        EXPERIENCE
        Senior Software Engineer at TechCorp (Jan 2020 - Present)
        - Led team of 5 engineers building scalable microservices using Go and Kubernetes
        - Architected migration from monolith to microservices, reducing deployment time by 80%
        - Implemented CI/CD pipelines with GitHub Actions, improving release frequency 10x
        
        Software Engineer at StartupXYZ (Jun 2017 - Dec 2019)
        - Built full-stack web applications using React, Node.js, and MongoDB
        - Designed RESTful APIs serving 100k+ daily requests
        - Implemented real-time features using WebSockets

        EDUCATION
        BS Computer Science | Stanford University | 2017

        SKILLS
        Languages: Go, Python, JavaScript, TypeScript, SQL
        Frameworks: React, Node.js, Express, Gin, gRPC
        Infrastructure: Kubernetes, Docker, AWS, Terraform
        Databases: PostgreSQL, MongoDB, Redis
        """

    def test_review_strong_resume(self, agent, strong_resume):
        """Test review of a strong resume."""
        result = agent.review(
            resume_text=strong_resume,
            target_role="software engineer",
        )

        assert isinstance(result, ResumeReviewResult)
        assert result.overall_score >= 80
        assert result.grade in ["A+", "A", "A-", "B+"]
        assert len(result.section_reviews) > 0
        assert len(result.strengths) > 0
        assert len(result.improvement_plan) > 0

    def test_review_weak_resume(self, agent):
        """Test review of a weak resume."""
        weak_resume = """
        John Doe
        Engineer
        
        Worked at companies. Know Python.
        
        Skills: Python, stuff
        """
        result = agent.review(resume_text=weak_resume, target_role="software engineer")

        assert result.overall_score < 70
        assert result.grade in ["C", "C-", "D", "F"]
        assert len(result.top_priorities) > 0

    def test_section_scoring(self, agent, strong_resume):
        """Test individual section scoring."""
        result = agent.review(resume_text=strong_resume, target_role="software engineer")

        for section_name, section_review in result.section_reviews.items():
            assert 0 <= section_review.score <= 100
            assert isinstance(section_review.issues, list)
            assert isinstance(section_review.strengths, list)
            assert isinstance(section_review.suggestions, list)

    def test_weak_phrase_detection(self, agent):
        """Test detection of weak passive language."""
        resume_with_weak = """
        John Doe
        john@email.com | (555) 123-4567
        
        EXPERIENCE
        Software Engineer at TechCorp (2020-Present)
        - Responsible for building APIs
        - Worked on microservices
        - Helped with deployments
        - Participated in code reviews
        - Familiar with Python and React
        """
        result = agent.review(resume_text=resume_with_weak, target_role="software engineer")

        exp_section = result.section_reviews.get("experience")
        weak_issues = [i for i in exp_section.issues if "weak" in i.title.lower() or "passive" in i.title.lower()]
        assert len(weak_issues) > 0

    def test_quantified_achievements_check(self, agent):
        """Test checking for quantified achievements."""
        resume_no_metrics = """
        John Doe
        john@email.com | (555) 123-4567
        
        EXPERIENCE
        Software Engineer at TechCorp (2020-Present)
        - Built scalable systems
        - Improved performance
        - Led team
        """
        result = agent.review(resume_text=resume_no_metrics, target_role="software engineer")

        exp_section = result.section_reviews.get("experience")
        metric_suggestions = [s for s in exp_section.suggestions if "quantif" in s.lower() or "metric" in s.lower()]
        assert len(metric_suggestions) > 0


class TestCoverLetterAgent:
    """Tests for CoverLetterAgent."""

    @pytest.fixture
    def agent(self):
        return CoverLetterAgent()

    @pytest.fixture
    def context(self):
        return CoverLetterContext(
            candidate_name="John Doe",
            candidate_email="john.doe@email.com",
            candidate_phone="(555) 123-4567",
            candidate_location="San Francisco, CA",
            target_role="Senior Software Engineer",
            target_company="Google",
            hiring_manager="Jane Smith",
            job_description="We are looking for a Senior Software Engineer with Python, React, AWS, Kubernetes experience...",
            key_skills=["Python", "React", "AWS", "Kubernetes", "Go"],
            key_achievements=[
                "Reduced deployment time by 80% through CI/CD improvements",
                "Led team of 5 engineers building microservices",
                "Architected migration from monolith to microservices",
            ],
            years_experience=8,
            current_role="Senior Software Engineer",
            tone=CoverLetterTone.PROFESSIONAL,
            length=CoverLetterLength.MEDIUM,
            linkedin_url="https://linkedin.com/in/johndoe",
            portfolio_url="https://github.com/johndoe",
        )

    def test_generate_cover_letter(self, agent, context):
        """Test cover letter generation."""
        result = agent.generate(context)

        assert isinstance(result, CoverLetterResult)
        assert len(result.content) > 100
        assert result.word_count > 150
        assert result.word_count < 400
        assert "John Doe" in result.content
        assert "Google" in result.content
        assert "Senior Software Engineer" in result.content

    def test_cover_letter_tone_variations(self, agent, context):
        """Test different tone options."""
        for tone in CoverLetterTone:
            context.tone = tone
            result = agent.generate(context)
            assert result.tone == tone
            assert len(result.content) > 50

    def test_cover_letter_length_variations(self, agent, context):
        """Test different length options."""
        for length in CoverLetterLength:
            context.length = length
            result = agent.generate(context)
            assert result.length == length

    def test_personalization_score(self, agent, context):
        """Test personalization scoring."""
        result = agent.generate(context)
        assert result.personalization_score >= 50
        assert result.personalization_score <= 100

    def test_key_points_covered(self, agent, context):
        """Test that key points are extracted."""
        result = agent.generate(context)
        assert len(result.key_points_covered) > 0
        assert any("80%" in p for p in result.key_points_covered)
        assert any("team" in p.lower() for p in result.key_points_covered)

    def test_suggestions_generation(self, agent, context):
        """Test suggestion generation."""
        result = agent.generate(context)
        assert isinstance(result.suggestions, list)


class TestApplicationAnswerAgent:
    """Tests for ApplicationAnswerAgent."""

    @pytest.fixture
    def agent(self):
        return ApplicationAnswerAgent()

    @pytest.fixture
    def candidate_profile(self):
        return {
            "name": "John Doe",
            "years_experience": 8,
            "skills": [
                {"name": "Python", "category": "technical", "proficiency": "expert", "years": 8},
                {"name": "React", "category": "technical", "proficiency": "advanced", "years": 5},
                {"name": "AWS", "category": "technical", "proficiency": "advanced", "years": 4},
                {"name": "Kubernetes", "category": "technical", "proficiency": "intermediate", "years": 2},
                {"name": "PostgreSQL", "category": "technical", "proficiency": "advanced", "years": 6},
            ],
            "achievements": [
                "Reduced deployment time by 80% through CI/CD pipeline improvements",
                "Led team of 5 engineers building scalable microservices",
                "Architected migration from monolith to microservices using Go and Kubernetes",
            ],
            "current_role": "Senior Software Engineer",
            "target_role": "Senior Software Engineer",
            "location": "San Francisco, CA",
            "notice_period": "2 weeks",
        }

    def test_generate_behavioral_answer(self, agent, candidate_profile):
        """Test STAR format behavioral answer generation."""
        question = ApplicationQuestion(
            question="Tell me about a time you led a challenging project.",
            question_type=QuestionType.BEHAVIORAL,
        )

        result = agent._generate_answer(question, candidate_profile, "Senior Software Engineer", "Google")

        assert result.strategy == AnswerStrategy.STAR
        assert "Situation:" in result.answer
        assert "Task:" in result.answer
        assert "Action:" in result.answer
        assert "Result:" in result.answer
        assert result.confidence > 60

    def test_generate_motivation_answer(self, agent, candidate_profile):
        """Test motivation answer generation."""
        question = ApplicationQuestion(
            question="Why do you want to work at Google?",
            question_type=QuestionType.MOTIVATION,
        )

        result = agent._generate_answer(question, candidate_profile, "Senior Software Engineer", "Google")

        assert "Google" in result.answer
        assert result.confidence > 50

    def test_generate_salary_answer(self, agent, candidate_profile):
        """Test salary expectation answer."""
        question = ApplicationQuestion(
            question="What are your salary expectations?",
            question_type=QuestionType.SALARY,
        )

        result = agent._generate_answer(question, candidate_profile, "Senior Software Engineer", "Google")

        assert "$" in result.answer
        assert "140" in result.answer or "150" in result.answer or "160" in result.answer  # Base ~144k+
        assert result.confidence > 60

    def test_generate_technical_answer(self, agent, candidate_profile):
        """Test technical answer generation."""
        question = ApplicationQuestion(
            question="How would you design a scalable system using Python and AWS?",
            question_type=QuestionType.TECHNICAL,
        )

        result = agent._generate_answer(question, candidate_profile, "Senior Software Engineer", "Google")

        assert result.strategy == AnswerStrategy.DIRECT
        assert any(kw in result.answer.lower() for kw in ["aws", "python", "scalable", "design"])

    def test_optimize_answer(self, agent):
        """Test answer optimization suggestions."""
        weak_answer = "I think I worked on some projects and helped with things. I'm responsible for coding."
        result = agent.optimize_answer(weak_answer, "Tell me about your experience")

        assert len(result["suggestions"]) > 0
        assert any("weak" in s.lower() or "responsible" in s.lower() for s in result["suggestions"])
        assert any("action" in s.lower() or "strong" in s.lower() for s in result["suggestions"])


class TestApplicationAgent:
    """Tests for ApplicationAgent orchestration."""

    @pytest.fixture
    def agent(self):
        return ApplicationAgent()

    @pytest.fixture
    def sample_resume(self):
        return """
        John Doe
        john.doe@email.com | (555) 123-4567 | San Francisco, CA
        LinkedIn: linkedin.com/in/johndoe

        SUMMARY
        Senior Software Engineer with 8 years experience in Python, React, AWS, Kubernetes.

        EXPERIENCE
        Senior Software Engineer at TechCorp (2020-Present)
        - Led team of 5 engineers building microservices
        - Reduced deployment time by 80%
        
        Software Engineer at StartupXYZ (2017-2020)
        - Built full-stack React/Node applications
        
        EDUCATION
        BS Computer Science, Stanford, 2017

        SKILLS
        Python, React, AWS, Kubernetes, Go, PostgreSQL
        """

    @pytest.fixture
    def candidate_profile(self):
        return {
            "name": "John Doe",
            "email": "john.doe@email.com",
            "phone": "(555) 123-4567",
            "location": "San Francisco, CA",
            "linkedin_url": "https://linkedin.com/in/johndoe",
            "portfolio_url": "https://github.com/johndoe",
            "years_experience": 8,
            "current_role": "Senior Software Engineer",
            "key_skills": ["Python", "React", "AWS", "Kubernetes", "Go"],
            "achievements": [
                "Reduced deployment time by 80% through CI/CD improvements",
                "Led team of 5 engineers building microservices",
                "Architected migration from monolith to microservices",
            ],
        }

    @pytest.mark.asyncio
    async def test_prepare_application_workflow(self, agent, sample_resume, candidate_profile):
        """Test full application preparation workflow."""
        result = await agent.prepare_application(
            user_id=1,
            job_id=123,
            company="Google",
            role="Senior Software Engineer",
            resume_text=sample_resume,
            candidate_profile=candidate_profile,
            target_role="Senior Software Engineer",
            target_company="Google",
            hiring_manager="Jane Smith",
            cover_letter_tone="professional",
            cover_letter_length="medium",
        )

        assert isinstance(result, ApplicationWorkflowResult)
        assert result.application_id is not None
        assert result.resume_ats_result is not None
        assert result.resume_review_result is not None
        assert result.cover_letter_result is not None
        assert isinstance(result.checklist, list)
        assert isinstance(result.next_steps, list)

    def test_optimize_resume(self, agent, sample_resume):
        """Test resume optimization."""
        result = agent.optimize_resume(
            resume_text=sample_resume,
            target_role="software engineer",
            job_description="Python, React, AWS, Kubernetes required",
        )

        assert "ats_score" in result
        assert "review_score" in result
        assert "recommendations" in result
        assert "improvement_plan" in result
        assert len(result["recommendations"]) > 0

    def test_optimize_cover_letter(self, agent):
        """Test cover letter optimization."""
        cover_letter = """
        Dear Hiring Manager,
        I am writing to apply for the Software Engineer position at Google.
        I have experience with Python and React.
        Sincerely,
        John Doe
        """
        result = agent.optimize_cover_letter(
            cover_letter=cover_letter,
            target_role="Software Engineer",
            target_company="Google",
        )

        assert "word_count" in result
        assert "suggestions" in result
        assert len(result["suggestions"]) > 0

    def test_prepare_for_interview(self, agent, candidate_profile):
        """Test interview preparation materials."""
        result = agent.prepare_for_interview(
            candidate_profile=candidate_profile,
            target_role="Senior Software Engineer",
            target_company="Google",
            job_description="Python, React, AWS, Kubernetes, leadership experience required",
        )

        assert "likely_questions" in result
        assert "star_stories" in result
        assert "company_research" in result
        assert "technical_preparation" in result
        assert "questions_to_ask" in result
        assert len(result["likely_questions"]) > 0
        assert len(result["star_stories"]) > 0

    def test_interview_questions_categories(self, agent, candidate_profile):
        """Test that interview questions cover multiple categories."""
        result = agent.prepare_for_interview(
            candidate_profile=candidate_profile,
            target_role="Senior Software Engineer",
            target_company="Google",
        )

        categories = set(q["category"] for q in result["likely_questions"])
        assert "Behavioral" in categories
        assert "Technical" in categories
        assert "Company Fit" in categories
        assert any("Leadership" in c for c in categories)  # Senior role


if __name__ == "__main__":
    pytest.main([__file__, "-v"])