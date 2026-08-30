import logging
import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum as PyEnum

from backend.agents.application.ats_resume_agent import ATSResumeAgent, ATSAnalysisResult
from backend.agents.application.resume_reviewer import ResumeReviewerAgent, ResumeReviewResult
from backend.agents.application.cover_letter_agent import CoverLetterAgent, CoverLetterContext, CoverLetterResult, CoverLetterTone, CoverLetterLength
from backend.agents.application.application_answer_agent import ApplicationAnswerAgent, ApplicationAnswersResult, ApplicationQuestion, QuestionType, AnswerStrategy

logger = logging.getLogger(__name__)


class ApplicationStatus(str, PyEnum):
    DRAFT = "draft"
    PREPARING = "preparing"
    READY_TO_SUBMIT = "ready_to_submit"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    INTERVIEW_SCHEDULED = "interview_scheduled"
    INTERVIEW_COMPLETED = "interview_completed"
    OFFER_RECEIVED = "offer_received"
    OFFER_ACCEPTED = "offer_accepted"
    OFFER_DECLINED = "offer_declined"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


@dataclass
class ApplicationPackage:
    """Complete application package for a job."""
    id: str
    user_id: int
    job_id: int
    company: str
    role: str
    status: ApplicationStatus = ApplicationStatus.DRAFT

    # Documents
    resume_text: Optional[str] = None
    resume_ats_score: Optional[float] = None
    resume_review_score: Optional[float] = None
    cover_letter: Optional[str] = None
    cover_letter_tone: str = "professional"

    # Application questions
    questions: List[Dict[str, Any]] = field(default_factory=list)
    answers: List[Dict[str, Any]] = field(default_factory=list)

    # Tracking
    applied_date: Optional[date] = None
    response_date: Optional[date] = None
    interview_date: Optional[date] = None
    notes: str = ""

    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ApplicationWorkflowResult:
    """Result of running the application workflow."""
    application_id: str
    resume_ats_result: Optional[ATSAnalysisResult] = None
    resume_review_result: Optional[ResumeReviewResult] = None
    cover_letter_result: Optional[CoverLetterResult] = None
    answers_result: Optional[ApplicationAnswersResult] = None
    ready_to_submit: bool = False
    checklist: List[Dict[str, Any]] = field(default_factory=list)
    next_steps: List[str] = field(default_factory=list)


class ApplicationAgent:
    """Orchestrate the complete application workflow."""

    def __init__(self):
        self.name = "application_agent"
        self.ats_agent = ATSResumeAgent()
        self.reviewer_agent = ResumeReviewerAgent()
        self.cover_letter_agent = CoverLetterAgent()
        self.answer_agent = ApplicationAnswerAgent()

    async def prepare_application(
        self,
        user_id: int,
        job_id: int,
        company: str,
        role: str,
        resume_text: str,
        candidate_profile: Dict[str, Any],
        job_description: Optional[str] = None,
        target_role: Optional[str] = None,
        target_company: Optional[str] = None,
        hiring_manager: Optional[str] = None,
        cover_letter_tone: str = "professional",
        cover_letter_length: str = "medium",
        weekly_learning_hours: int = 10,
    ) -> ApplicationWorkflowResult:
        """Run the complete application preparation workflow."""
        logger.info(f"Preparing application for user {user_id}: {role} at {company}")

        application_id = f"app_{user_id}_{job_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

        # 1. ATS Analysis
        logger.info("Running ATS analysis...")
        ats_result = self.ats_agent.analyze(
            resume_text=resume_text,
            target_role=target_role,
            job_description=job_description,
        )

        # 2. Resume Review
        logger.info("Running resume review...")
        review_result = self.reviewer_agent.review(
            resume_text=resume_text,
            target_role=target_role,
        )

        # 3. Cover Letter Generation
        logger.info("Generating cover letter...")
        cover_letter_result = None
        if target_company:
            cl_context = CoverLetterContext(
                candidate_name=candidate_profile.get("name", "Candidate"),
                candidate_email=candidate_profile.get("email", ""),
                candidate_phone=candidate_profile.get("phone", ""),
                candidate_location=candidate_profile.get("location", ""),
                target_role=target_role or role,
                target_company=target_company or company,
                hiring_manager=hiring_manager,
                job_description=job_description,
                key_skills=candidate_profile.get("key_skills", []),
                key_achievements=candidate_profile.get("achievements", []),
                years_experience=candidate_profile.get("years_experience", 0),
                current_role=candidate_profile.get("current_role", ""),
                tone=CoverLetterTone(cover_letter_tone),
                length=CoverLetterLength(cover_letter_length),
                linkedin_url=candidate_profile.get("linkedin_url"),
                portfolio_url=candidate_profile.get("portfolio_url"),
            )
            cover_letter_result = self.cover_letter_agent.generate(cl_context)

        # 4. Answer Generation
        answers_result = None
        # This would be called when user provides application questions
        # For now, return None

        # 5. Checklist & Next Steps
        checklist = self._generate_checklist(
            ats_result, review_result, cover_letter_result, answers_result
        )
        next_steps = self._generate_next_steps(
            ats_result, review_result, cover_letter_result
        )

        ready = self._is_ready_to_submit(
            ats_result, review_result, cover_letter_result
        )

        return ApplicationWorkflowResult(
            application_id=application_id,
            resume_ats_result=ats_result,
            resume_review_result=review_result,
            cover_letter_result=cover_letter_result,
            answers_result=answers_result,
            ready_to_submit=ready,
            checklist=checklist,
            next_steps=next_steps,
        )

    def generate_cover_letter(
        self,
        candidate_profile: Dict[str, Any],
        target_role: str,
        target_company: str,
        job_description: Optional[str] = None,
        hiring_manager: Optional[str] = None,
        tone: str = "professional",
        length: str = "medium",
    ) -> CoverLetterResult:
        """Generate cover letter for a specific application."""
        cl_context = CoverLetterContext(
            candidate_name=candidate_profile.get("name", "Candidate"),
            candidate_email=candidate_profile.get("email", ""),
            candidate_phone=candidate_profile.get("phone", ""),
            candidate_location=candidate_profile.get("location", ""),
            target_role=target_role,
            target_company=target_company,
            hiring_manager=hiring_manager,
            job_description=job_description,
            key_skills=candidate_profile.get("key_skills", []),
            key_achievements=candidate_profile.get("achievements", []),
            years_experience=candidate_profile.get("years_experience", 0),
            current_role=candidate_profile.get("current_role", ""),
            tone=CoverLetterTone(tone),
            length=CoverLetterLength(length),
            linkedin_url=candidate_profile.get("linkedin_url"),
            portfolio_url=candidate_profile.get("portfolio_url"),
        )
        return self.cover_letter_agent.generate(cl_context)

    def generate_answers(
        self,
        questions: List[str],
        candidate_profile: Dict[str, Any],
        target_role: Optional[str] = None,
        target_company: Optional[str] = None,
    ) -> ApplicationAnswersResult:
        """Generate answers for application questions."""
        questions_obj = [
            ApplicationQuestion(
                question=q,
                question_type=self.answer_agent._classify_question(q),
            )
            for q in questions
        ]
        return self.answer_agent.generate_answers(
            questions_obj, candidate_profile, target_role, target_company
        )

    def optimize_resume(
        self,
        resume_text: str,
        target_role: Optional[str] = None,
        job_description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Provide comprehensive resume optimization suggestions."""
        ats_result = self.ats_agent.analyze(resume_text, target_role, job_description)
        review_result = self.reviewer_agent.review(resume_text, target_role)

        return {
            "ats_score": ats_result.overall_score,
            "ats_passed": ats_result.passed,
            "review_score": review_result.overall_score,
            "review_grade": review_result.grade,
            "ats_issues": [i.to_dict() for i in ats_result.issues],
            "review_issues": [i.to_dict() for s in review_result.section_reviews.values() for i in s.issues],
            "missing_keywords": ats_result.missing_keywords,
            "recommendations": ats_result.recommendations + review_result.top_priorities,
            "improvement_plan": review_result.improvement_plan,
        }

    def optimize_cover_letter(
        self,
        cover_letter: str,
        target_role: str,
        target_company: str,
    ) -> Dict[str, Any]:
        """Provide optimization suggestions for cover letter."""
        # Use the cover letter agent's suggestions
        # This is a simplified version - in production would be more sophisticated
        suggestions = []

        word_count = len(cover_letter.split())
        if word_count < 150:
            suggestions.append("Cover letter is too short -- aim for 250-350 words")
        elif word_count > 400:
            suggestions.append("Cover letter is too long -- aim for 250-350 words")

        company_mentions = cover_letter.lower().count(target_company.lower())
        if company_mentions < 2:
            suggestions.append(f"Mention {target_company} more often to show genuine interest")

        if "I am writing to apply" in cover_letter:
            suggestions.append("Use a more engaging opening than 'I am writing to apply'")

        if "Sincerely" not in cover_letter:
            suggestions.append("Add professional closing with signature")

        return {
            "word_count": word_count,
            "suggestions": suggestions,
            "company_mentions": company_mentions,
        }

    def prepare_for_interview(
        self,
        candidate_profile: Dict[str, Any],
        target_role: str,
        target_company: str,
        job_description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Prepare interview preparation materials."""
        # Generate likely interview questions
        questions = self._generate_interview_questions(
            candidate_profile, target_role, target_company, job_description
        )

        # Generate STAR stories from profile
        star_stories = self._generate_star_stories(candidate_profile)

        # Company research prompts
        company_research = self._generate_company_research_prompts(target_company)

        # Technical preparation
        tech_prep = self._generate_technical_prep(candidate_profile, target_role)

        return {
            "likely_questions": questions,
            "star_stories": star_stories,
            "company_research": company_research,
            "technical_preparation": tech_prep,
            "questions_to_ask": self._generate_questions_to_ask(target_company, target_role),
        }

    def _generate_interview_questions(
        self,
        profile: Dict,
        role: str,
        company: str,
        job_description: Optional[str],
    ) -> List[Dict[str, Any]]:
        """Generate likely interview questions."""
        questions = []

        # Behavioral
        questions.extend([
            {"category": "Behavioral", "question": "Tell me about a time you led a challenging project.", "type": "STAR"},
            {"category": "Behavioral", "question": "Describe a situation where you had a conflict with a colleague.", "type": "STAR"},
            {"category": "Behavioral", "question": "Tell me about a time you failed and what you learned.", "type": "STAR"},
        ])

        # Technical
        skills = profile.get("skills", [])
        for skill in [s.get("name") for s in skills[:3]]:
            questions.append({
                "category": "Technical",
                "question": f"Walk me through how you would implement a solution using {skill}.",
                "type": "Technical Deep Dive",
            })

        # Role-specific
        if "senior" in role.lower() or "lead" in role.lower():
            questions.append({
                "category": "Leadership",
                "question": "How do you approach technical decision-making and mentoring?",
                "type": "Discussion",
            })

        # Company-specific
        if company:
            questions.append({
                "category": "Company Fit",
                "question": f"Why {company}? What do you know about our mission and products?",
                "type": "Motivation",
            })

        return questions

    def _generate_star_stories(self, profile: Dict) -> List[Dict[str, str]]:
        """Generate STAR stories from profile achievements."""
        stories = []
        achievements = profile.get("achievements", [])

        for achievement in achievements[:5]:
            stories.append({
                "title": achievement.get("title", "Key Achievement"),
                "situation": achievement.get("situation", "In my previous role..."),
                "task": achievement.get("task", "I was tasked with..."),
                "action": achievement.get("action", "I took the following steps..."),
                "result": achievement.get("result", "The outcome was..."),
                "skills_demonstrated": achievement.get("skills", []),
            })

        return stories

    def _generate_company_research_prompts(self, company: str) -> List[str]:
        """Generate research prompts for company."""
        return [
            f"What is {company}'s mission statement and core values?",
            f"What are {company}'s main products/services and target market?",
            f"Recent news: funding rounds, acquisitions, product launches, leadership changes",
            f"Company culture: Glassdoor reviews, employee testimonials, engineering blog",
            f"Competitors and market position",
            f"Tech stack: what technologies do they use? (check job postings, engineering blog)",
            f"Recent technical challenges they've solved (engineering blog, conference talks)",
        ]

    def _generate_technical_prep(
        self,
        profile: Dict,
        role: str,
    ) -> Dict[str, Any]:
        """Generate technical preparation guide."""
        skills = [s.get("name") for s in profile.get("skills", [])]

        return {
            "core_skills_to_review": skills[:5],
            "system_design_topics": [
                "Scalability patterns",
                "Database design (SQL vs NoSQL)",
                "Caching strategies",
                "Message queues and event-driven architecture",
                "API design (REST, GraphQL, gRPC)",
                "Microservices vs monolith",
            ],
            "coding_patterns": [
                "Two pointers / sliding window",
                "BFS/DFS on trees and graphs",
                "Dynamic programming",
                "Heap / priority queue",
                "Binary search variations",
            ],
            "behavioral_prep": [
                "Prepare 3 STAR stories: leadership, conflict, failure/learning",
                "Prepare 'why this company' and 'why this role' answers",
                "Prepare questions to ask interviewer",
            ],
        }

    def _generate_questions_to_ask(self, company: str, role: str) -> List[str]:
        """Generate questions for the candidate to ask."""
        return [
            f"What does success look like in this {role} role in the first 90 days?",
            f"What's the biggest technical challenge the team is currently facing?",
            "How does the team approach technical debt and code quality?",
            "What's the deployment process and how often do you release?",
            "How does the team handle on-call and incident response?",
            "What opportunities are there for mentorship and professional development?",
            "How does engineering collaborate with product and design?",
            "What's the team's approach to architecture decisions and RFCs?",
            f"What's {company}'s approach to work-life balance and remote work?",
            "What's one thing you'd change about the engineering culture?",
        ]

    def _generate_checklist(
        self,
        ats_result: Optional[ATSAnalysisResult],
        review_result: Optional[ResumeReviewResult],
        cover_letter_result: Optional[CoverLetterResult],
        answers_result: Optional[ApplicationAnswersResult],
    ) -> List[Dict[str, Any]]:
        """Generate application readiness checklist."""
        checklist = []

        # Resume ATS
        if ats_result:
            checklist.append({
                "item": f"ATS Compatibility Score: {ats_result.overall_score}/100",
                "status": "pass" if ats_result.passed else "fail",
                "priority": "high",
            })

        # Resume Review
        if review_result:
            checklist.append({
                "item": f"Resume Quality Score: {review_result.overall_score}/100 ({review_result.grade})",
                "status": "pass" if review_result.overall_score >= 80 else "review",
                "priority": "high",
            })

        # Cover Letter
        if cover_letter_result:
            checklist.append({
                "item": f"Cover Letter Generated ({cover_letter_result.word_count} words, {cover_letter_result.length.value})",
                "status": "pass",
                "priority": "medium",
            })
        else:
            checklist.append({
                "item": "Cover Letter Generated",
                "status": "missing",
                "priority": "medium",
            })

        # Keyword Match
        if ats_result:
            checklist.append({
                "item": f"Keyword Match: {ats_result.keyword_match_score}%",
                "status": "pass" if ats_result.keyword_match_score >= 70 else "review",
                "priority": "high",
            })

        # Missing Keywords
        if ats_result and ats_result.missing_keywords:
            checklist.append({
                "item": f"Missing Keywords: {', '.join(ats_result.missing_keywords[:5])}",
                "status": "action_needed",
                "priority": "high",
            })

        return checklist

    def _generate_next_steps(
        self,
        ats_result: Optional[ATSAnalysisResult],
        review_result: Optional[ResumeReviewResult],
        cover_letter_result: Optional[CoverLetterResult],
    ) -> List[str]:
        """Generate next steps based on analysis results."""
        steps = []

        if ats_result and not ats_result.passed:
            steps.append(f"Improve ATS score: add missing keywords ({', '.join(ats_result.missing_keywords[:3])})")

        if review_result and review_result.overall_score < 80:
            if review_result.top_priorities:
                steps.append(f"Address top resume issues: {review_result.top_priorities[0]}")

        if not cover_letter_result:
            steps.append("Generate tailored cover letter for the application")

        steps.append("Prepare STAR stories for behavioral interviews")
        steps.append("Research company thoroughly before applying")
        steps.append("Prepare 3-5 questions to ask the interviewer")

        return steps[:5]

    def _is_ready_to_submit(
        self,
        ats_result: Optional[ATSAnalysisResult],
        review_result: Optional[ResumeReviewResult],
        cover_letter_result: Optional[CoverLetterResult],
    ) -> bool:
        """Determine if application is ready to submit."""
        if ats_result and not ats_result.passed:
            return False
        if review_result and review_result.overall_score < 70:
            return False
        if not cover_letter_result:
            return False
        return True


from typing import Optional