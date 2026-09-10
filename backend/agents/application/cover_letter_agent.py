import logging
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum as PyEnum

logger = logging.getLogger(__name__)


class CoverLetterTone(str, PyEnum):
    PROFESSIONAL = "professional"
    CONVERSATIONAL = "conversational"
    ENTHUSIASTIC = "enthusiastic"
    FORMAL = "formal"
    CREATIVE = "creative"


class CoverLetterLength(str, PyEnum):
    SHORT = "short"      # ~150-200 words
    MEDIUM = "medium"    # ~250-350 words
    LONG = "long"        # ~400-500 words


@dataclass
class CoverLetterContext:
    """Context for cover letter generation."""
    candidate_name: str
    candidate_email: str
    candidate_phone: str
    candidate_location: str
    target_role: str
    target_company: str
    hiring_manager: Optional[str] = None
    job_description: Optional[str] = None
    key_skills: List[str] = field(default_factory=list)
    key_achievements: List[str] = field(default_factory=list)
    years_experience: int = 0
    current_role: Optional[str] = None
    referral: Optional[str] = None
    tone: CoverLetterTone = CoverLetterTone.PROFESSIONAL
    length: CoverLetterLength = CoverLetterLength.MEDIUM
    linkedin_url: Optional[str] = None
    portfolio_url: Optional[str] = None


@dataclass
class CoverLetterResult:
    """Generated cover letter with metadata."""
    content: str
    word_count: int
    tone: CoverLetterTone
    length: CoverLetterLength
    key_points_covered: List[str]
    personalization_score: float  # 0-100
    suggestions: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "word_count": self.word_count,
            "tone": self.tone.value if hasattr(self.tone, "value") else str(self.tone),
            "length": self.length.value if hasattr(self.length, "value") else str(self.length),
            "key_points_covered": self.key_points_covered,
            "personalization_score": self.personalization_score,
            "suggestions": self.suggestions,
        }


class CoverLetterAgent:
    """Generate personalized cover letters."""

    def __init__(self):
        self.name = "cover_letter_agent"

        # Opening templates by tone
        self.openings = {
            CoverLetterTone.PROFESSIONAL: [
                "I am writing to express my strong interest in the {role} position at {company}.",
                "I am excited to apply for the {role} role at {company}.",
                "With {years} years of experience in {field}, I am eager to bring my expertise to {company} as a {role}.",
            ],
            CoverLetterTone.ENTHUSIASTIC: [
                "I was thrilled to discover the {role} opening at {company}!",
                "When I saw the {role} position at {company}, I knew I had to apply.",
                "I've long admired {company}'s work in {industry}, and I'm excited about the opportunity to contribute as a {role}.",
            ],
            CoverLetterTone.CONVERSATIONAL: [
                "I've been following {company}'s work for some time, and the {role} position caught my attention.",
                "I wanted to reach out about the {role} role at {company} -- it feels like a great fit.",
            ],
            CoverLetterTone.FORMAL: [
                "I am writing to formally apply for the position of {role} at {company}.",
                "Please accept my application for the {role} position at {company}.",
            ],
            CoverLetterTone.CREATIVE: [
                "What if your next {role} could {unique_value}? That's the question that led me to {company}.",
                "They say the best {role}s don't just write code -- they solve problems. Here's how I've been doing that at {company}.",
            ],
        }

        # Body paragraph templates
        self.body_templates = {
            "experience_match": (
                "In my current role as {current_role} at {current_company}, I have {key_achievement}. "
                "This experience has honed my skills in {key_skills}, which directly align with your requirements for {target_role}."
            ),
            "achievement_highlight": (
                "One of my proudest accomplishments was {achievement}. "
                "This demonstrates my ability to {skill_demonstrated}, a key competency for this role."
            ),
            "skill_alignment": (
                "Your job description emphasizes {key_requirement}. "
                "Throughout my {years} years of experience, I have consistently {skill_action} using {relevant_skills}."
            ),
            "company_alignment": (
                "I have long admired {company}'s work in {company_domain}, particularly {specific_project}. "
                "Your commitment to {company_value} resonates with my own professional philosophy."
            ),
            "transition_explanation": (
                "While my background is in {previous_field}, I have actively transitioned to {target_field} by {transition_action}. "
                "This unique perspective allows me to {unique_value}."
            ),
        }

        # Closing templates
        self.closings = {
            CoverLetterTone.PROFESSIONAL: [
                "Thank you for your time and consideration. I look forward to discussing how I can contribute to {company}.",
                "I would welcome the opportunity to discuss how my experience aligns with your needs.",
            ],
            CoverLetterTone.ENTHUSIASTIC: [
                "I'm excited about the possibility of joining {company} and contributing to {company_mission}!",
                "I'd love to chat about how I can help {company} achieve its goals.",
            ],
            CoverLetterTone.CONVERSATIONAL: [
                "I'd love to chat more about how I could contribute to the team.",
                "Let me know if you'd like to hear more about my experience with {key_skill}.",
            ],
            CoverLetterTone.FORMAL: [
                "I appreciate your consideration and look forward to your response.",
                "Thank you for your time and consideration.",
            ],
            CoverLetterTone.CREATIVE: [
                "Let's build something great together. I'm ready when you are.",
                "P.S. I've included a link to my portfolio at {portfolio_url} -- would love your feedback!",
            ],
        }

    def generate(
        self,
        context: CoverLetterContext,
    ) -> CoverLetterResult:
        """Generate a personalized cover letter."""
        logger.info(f"Generating cover letter for {context.target_role} at {context.target_company}")

        # Build opening
        opening = self._generate_opening(context)

        # Build body paragraphs
        body_paragraphs = self._generate_body_paragraphs(context)

        # Build closing
        closing = self._generate_closing(context)

        # Combine
        content = self._assemble_letter(context, opening, body_paragraphs, closing)

        # Calculate metrics
        word_count = len(content.split())
        key_points = self._extract_key_points(content, context)
        personalization_score = self._calculate_personalization(content, context)
        suggestions = self._generate_suggestions(context, word_count)

        return CoverLetterResult(
            content=content,
            word_count=word_count,
            tone=context.tone,
            length=context.length,
            key_points_covered=key_points,
            personalization_score=personalization_score,
            suggestions=suggestions,
        )

    def _generate_opening(self, context: CoverLetterContext) -> str:
        """Generate opening paragraph."""
        templates = self.openings.get(context.tone, self.openings[CoverLetterTone.PROFESSIONAL])

        # Select template based on context
        if context.referral:
            template = "I was referred to this position by {referral}, who thought I'd be a great fit for the {role} role at {company}."
        elif context.tone == CoverLetterTone.CREATIVE and context.years_experience > 5:
            template = templates[0]
        else:
            template = templates[0]

        return template.format(
            role=context.target_role,
            company=context.target_company,
            years=context.years_experience,
            field=context.current_role or "the industry",
            industry=self._infer_industry(context.target_company),
            referral=context.referral or "a colleague",
            unique_value="drive innovation through AI",
        )

    def _generate_body_paragraphs(self, context: CoverLetterContext) -> List[str]:
        """Generate body paragraphs."""
        paragraphs = []

        # Paragraph 1: Experience match
        if context.current_role and context.key_achievements:
            para = self.body_templates["experience_match"].format(
                current_role=context.current_role,
                current_company="my current company",
                key_achievement=context.key_achievements[0] if context.key_achievements else "delivered significant results",
                key_skills=", ".join(context.key_skills[:3]),
                target_role=context.target_role,
            )
            paragraphs.append(para)

        # Paragraph 2: Key achievement
        if len(context.key_achievements) > 1:
            para = self.body_templates["achievement_highlight"].format(
                achievement=context.key_achievements[1],
                skill_demonstrated="deliver high-impact results",
            )
            paragraphs.append(para)

        # Paragraph 3: Skill alignment with job description
        if context.job_description:
            # Extract key requirement from JD (simplified)
            jd_keywords = self._extract_jd_keywords(context.job_description)
            if jd_keywords:
                para = self.body_templates["skill_alignment"].format(
                    key_requirement=jd_keywords[0],
                    years=context.years_experience,
                    skill_action="delivered solutions using",
                    relevant_skills=", ".join(context.key_skills[:3]),
                )
                paragraphs.append(para)

        # Paragraph 4: Company alignment
        if context.target_company:
            para = self.body_templates["company_alignment"].format(
                company=context.target_company,
                company_domain=self._infer_industry(context.target_company),
                specific_project="your innovative work",
                company_value="innovation and excellence",
            )
            paragraphs.append(para)

        return paragraphs

    def _generate_closing(self, context: CoverLetterContext) -> str:
        """Generate closing paragraph."""
        templates = self.closings.get(context.tone, self.closings[CoverLetterTone.PROFESSIONAL])
        template = templates[0]

        return template.format(
            company=context.target_company,
            company_mission="your mission",
            portfolio_url=context.portfolio_url or "my portfolio",
            key_skill=context.key_skills[0] if context.key_skills else "my expertise",
        )

    def _assemble_letter(
        self,
        context: CoverLetterContext,
        opening: str,
        body_paragraphs: List[str],
        closing: str,
    ) -> str:
        """Assemble the complete cover letter."""
        hiring_manager_salutation = f"Dear {context.hiring_manager}," if context.hiring_manager else "Dear Hiring Manager,"

        # Header
        header = f"""{context.candidate_name}
{context.candidate_email} | {context.candidate_phone} | {context.candidate_location}
{context.linkedin_url or ''}
{context.portfolio_url or ''}

{datetime.now().strftime('%B %d, %Y')}

{hiring_manager_salutation}

"""

        # Body
        body = opening + "\n\n" + "\n\n".join(body_paragraphs) + "\n\n" + closing

        # Signature
        signature = f"\n\nSincerely,\n{context.candidate_name}"

        return header + body + signature

    def _extract_jd_keywords(self, job_description: str) -> List[str]:
        """Extract key requirements from job description."""
        # Simplified extraction - in production would use NLP
        keywords = [
            "python", "javascript", "react", "aws", "kubernetes", "docker",
            "sql", "machine learning", "leadership", "agile", "ci/cd",
        ]
        jd_lower = job_description.lower()
        return [kw for kw in keywords if kw in jd_lower]

    def _infer_industry(self, company: str) -> str:
        """Infer industry from company name."""
        tech_companies = ["google", "microsoft", "amazon", "meta", "apple", "netflix", "uber", "airbnb", "stripe"]
        if any(tc in company.lower() for tc in tech_companies):
            return "technology"
        return "your industry"

    def _extract_key_points(self, content: str, context: CoverLetterContext) -> List[str]:
        """Extract key points covered in the letter."""
        points = []

        if context.key_achievements:
            points.append(f"Highlighted achievement: {context.key_achievements[0]}")

        if context.key_skills:
            points.append(f"Emphasized skills: {', '.join(context.key_skills[:3])}")

        if context.years_experience:
            points.append(f"Mentioned {context.years_experience} years of experience")

        if context.target_company:
            points.append(f"Tailored for {context.target_company}")

        if context.referral:
            points.append(f"Mentioned referral from {context.referral}")

        return points

    def _calculate_personalization(self, content: str, context: CoverLetterContext) -> float:
        """Calculate personalization score (0-100)."""
        score = 50  # Base score

        # Company name mentions
        company_mentions = content.lower().count(context.target_company.lower())
        score += min(company_mentions * 5, 20)

        # Role mentions
        role_mentions = content.lower().count(context.target_role.lower())
        score += min(role_mentions * 3, 15)

        # Specific achievements mentioned
        for achievement in context.key_achievements:
            achievement_str = achievement.get("result", achievement) if isinstance(achievement, dict) else achievement
            if achievement_str.lower()[:20] in content.lower():
                score += 5

        # Skills mentioned
        for skill in context.key_skills:
            if skill.lower() in content.lower():
                score += 2

        # Hiring manager addressed
        if context.hiring_manager and context.hiring_manager.lower() in content.lower():
            score += 10

        return min(100, score)

    def _generate_suggestions(self, context: CoverLetterContext, word_count: int) -> List[str]:
        """Generate improvement suggestions."""
        suggestions = []

        if word_count < 150:
            suggestions.append("Letter is quite short. Consider adding more detail about your achievements.")
        elif word_count > 400:
            suggestions.append("Letter is long. Consider condensing to 250-350 words for better readability.")

        if not context.hiring_manager:
            suggestions.append("Try to find the hiring manager's name for a more personalized greeting.")

        if not context.job_description:
            suggestions.append("Provide the job description for better keyword alignment.")

        if len(context.key_achievements) < 2:
            suggestions.append("Add more specific achievements with metrics to strengthen your case.")

        if not context.portfolio_url:
            suggestions.append("Consider adding a portfolio or GitHub link to showcase your work.")

        return suggestions[:5]


from typing import Optional