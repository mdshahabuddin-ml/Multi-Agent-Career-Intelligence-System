import logging
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum as PyEnum

logger = logging.getLogger(__name__)


class ReviewCategory(str, PyEnum):
    CONTENT = "content"
    STRUCTURE = "structure"
    FORMATTING = "formatting"
    IMPACT = "impact"
    RELEVANCE = "relevance"


class IssueSeverity(str, PyEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    SUGGESTION = "suggestion"


@dataclass
class ReviewIssue:
    """An issue found during resume review."""
    category: ReviewCategory
    severity: IssueSeverity
    title: str
    description: str
    suggestion: str
    section: Optional[str] = None
    examples: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category.value if hasattr(self.category, "value") else str(self.category),
            "severity": self.severity.value if hasattr(self.severity, "value") else str(self.severity),
            "title": self.title,
            "description": self.description,
            "suggestion": self.suggestion,
            "section": self.section,
            "examples": self.examples,
        }


@dataclass
class SectionReview:
    """Review of a specific resume section."""
    section_name: str
    score: float  # 0-100
    issues: List[ReviewIssue]
    strengths: List[str]
    suggestions: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "section_name": self.section_name,
            "score": self.score,
            "issues": [i.to_dict() for i in self.issues],
            "strengths": self.strengths,
            "suggestions": self.suggestions,
        }


@dataclass
class ResumeReviewResult:
    """Complete resume review result."""
    overall_score: float  # 0-100
    grade: str  # A+, A, A-, B+, B, B-, C+, C, C-, D, F
    section_reviews: Dict[str, SectionReview]
    top_priorities: List[str]
    strengths: List[str]
    overall_feedback: str
    improvement_plan: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_score": self.overall_score,
            "grade": self.grade,
            "section_reviews": {k: v.to_dict() for k, v in self.section_reviews.items()},
            "top_priorities": self.top_priorities,
            "strengths": self.strengths,
            "overall_feedback": self.overall_feedback,
            "improvement_plan": self.improvement_plan,
        }


class ResumeReviewerAgent:
    """Comprehensive resume content and quality review."""

    def __init__(self):
        self.name = "resume_reviewer_agent"

        # Strong action verbs by category
        self.action_verbs = {
            "leadership": ["led", "directed", "managed", "supervised", "mentored", "guided", "orchestrated", "spearheaded"],
            "achievement": ["achieved", "delivered", "exceeded", "surpassed", "accomplished", "attained", "realized"],
            "creation": ["built", "created", "designed", "developed", "engineered", "architected", "constructed", "produced"],
            "improvement": ["improved", "optimized", "enhanced", "streamlined", "refined", "upgraded", "modernized", "transformed"],
            "cost_saving": ["reduced", "decreased", "minimized", "cut", "saved", "conserved", "eliminated"],
            "growth": ["increased", "grew", "expanded", "scaled", "boosted", "accelerated", "amplified"],
            "technical": ["implemented", "developed", "engineered", "coded", "programmed", "debugged", "deployed", "integrated"],
            "analysis": ["analyzed", "evaluated", "assessed", "investigated", "diagnosed", "researched", "audited"],
            "collaboration": ["collaborated", "partnered", "coordinated", "facilitated", "negotiated", "mediated"],
            "innovation": ["innovated", "pioneered", "introduced", "launched", "pioneered", "conceptualized"],
        }

        # Weak phrases to avoid
        self.weak_phrases = [
            "responsible for", "duties included", "worked on", "helped with",
            "assisted with", "participated in", "involved in", "supported",
            "familiar with", "knowledge of", "exposure to", "experience with",
            "good communication skills", "team player", "hard worker",
            "detail-oriented", "fast learner", "self-motivated",
        ]

        # Strong replacements
        self.strong_replacements = {
            "responsible for": "managed",
            "duties included": "executed",
            "worked on": "developed",
            "helped with": "contributed to",
            "assisted with": "supported",
            "participated in": "contributed to",
            "involved in": "engaged in",
            "supported": "enabled",
            "familiar with": "proficient in",
            "knowledge of": "expertise in",
            "exposure to": "hands-on experience with",
            "experience with": "skilled in",
        }

    def review(
        self,
        resume_text: str,
        target_role: Optional[str] = None,
        target_company: Optional[str] = None,
    ) -> ResumeReviewResult:
        """Comprehensive resume review."""
        logger.info(f"Reviewing resume for {target_role or 'general'} position")

        # Split into sections
        sections = self._extract_sections(resume_text)

        # Review each section
        section_reviews = {}
        for section_name, section_content in sections.items():
            section_reviews[section_name] = self._review_section(
                section_name, section_content, target_role
            )

        # Calculate overall score
        overall_score = self._calculate_overall_score(section_reviews)

        # Determine grade
        grade = self._score_to_grade(overall_score)

        # Identify top priorities
        top_priorities = self._identify_priorities(section_reviews)

        # Collect strengths
        strengths = self._collect_strengths(section_reviews)

        # Generate overall feedback
        overall_feedback = self._generate_overall_feedback(overall_score, section_reviews)

        # Create improvement plan
        improvement_plan = self._create_improvement_plan(section_reviews)

        return ResumeReviewResult(
            overall_score=round(overall_score, 1),
            grade=grade,
            section_reviews=section_reviews,
            top_priorities=top_priorities,
            strengths=strengths,
            overall_feedback=overall_feedback,
            improvement_plan=improvement_plan,
        )

    def _extract_sections(self, text: str) -> Dict[str, str]:
        """Extract resume sections."""
        sections = {}
        section_patterns = {
            "summary": [r"(?:summary|profile|objective|about me)[\s:]*\n(.*?)(?=\n\s*(?:[A-Z][A-Z\s]+)[\s:]*\n|$)"],
            "experience": [r"(?:experience|work history|employment)[\s:]*\n(.*?)(?=\n\s*(?:[A-Z][A-Z\s]+)[\s:]*\n|$)"],
            "education": [r"(?:education|academic)[\s:]*\n(.*?)(?=\n\s*(?:[A-Z][A-Z\s]+)[\s:]*\n|$)"],
            "skills": [r"(?:skills|technologies|technical)[\s:]*\n(.*?)(?=\n\s*(?:[A-Z][A-Z\s]+)[\s:]*\n|$)"],
            "projects": [r"(?:projects|portfolio)[\s:]*\n(.*?)(?=\n\s*(?:[A-Z][A-Z\s]+)[\s:]*\n|$)"],
            "certifications": [r"(?:certifications|certificates)[\s:]*\n(.*?)(?=\n\s*(?:[A-Z][A-Z\s]+)[\s:]*\n|$)"],
        }

        result = {}
        for section, patterns in section_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
                if match:
                    result[section] = match.group(1).strip()
                    break
            if section not in result:
                result[section] = ""

        return result

    def _review_section(
        self,
        section_name: str,
        content: str,
        target_role: Optional[str],
    ) -> SectionReview:
        """Review a specific resume section."""
        issues = []
        strengths = []
        suggestions = []

        if not content or len(content.strip()) < 20:
            issues.append(ReviewIssue(
                category=ReviewCategory.CONTENT,
                severity=IssueSeverity.HIGH if section_name in ["experience", "education", "skills"] else IssueSeverity.MEDIUM,
                title=f"Missing or insufficient {section_name}",
                description=f"The {section_name} section is empty or too brief",
                suggestion=f"Add a comprehensive {section_name} section with relevant details",
                section=section_name,
            ))
            return SectionReview(section_name, 0, issues, [], [])

        # Review based on section type
        if section_name == "summary":
            return self._review_summary(content)
        elif section_name == "experience":
            return self._review_experience(content)
        elif section_name == "education":
            return self._review_education(content)
        elif section_name == "skills":
            return self._review_skills(content)
        elif section_name == "projects":
            return self._review_projects(content)
        elif section_name == "certifications":
            return self._review_certifications(content)
        else:
            # Generic review
            return self._review_generic(section_name, content)

    def _review_summary(self, content: str) -> SectionReview:
        """Review professional summary."""
        issues = []
        strengths = []
        suggestions = []

        word_count = len(content.split())

        if word_count < 30:
            issues.append(ReviewIssue(
                category=ReviewCategory.CONTENT,
                severity=IssueSeverity.HIGH,
                title="Summary too brief",
                description=f"Only {word_count} words. Summary should be 3-5 sentences highlighting your value proposition.",
                suggestion="Expand to 50-100 words highlighting your years of experience, key skills, and career highlights.",
            ))
        elif word_count > 150:
            issues.append(ReviewIssue(
                category=ReviewCategory.CONTENT,
                severity=IssueSeverity.MEDIUM,
                title="Summary too long",
                description=f"{word_count} words exceeds recommended length.",
                suggestion="Condense to 3-5 impactful sentences focusing on your unique value.",
            ))
        else:
            strengths.append("Good summary length")

        # Check for keywords
        keywords = ["experience", "years", "skilled", "expertise", "proven", "track record"]
        found = sum(1 for kw in keywords if kw in content.lower())
        if found < 2:
            suggestions.append("Include keywords like 'years of experience', 'proven track record', 'expertise in'")

        # Check for quantified value
        if not re.search(r"\d+", content):
            suggestions.append("Add quantifiable achievement (e.g., '10+ years', '50% improvement', '$1M revenue')")

        score = max(0, 100 - len(issues) * 20 - len(suggestions) * 5)
        return SectionReview("summary", score, issues, strengths, suggestions)

    def _review_experience(self, content: str) -> SectionReview:
        """Review experience section."""
        issues = []
        strengths = []
        suggestions = []

        # Check for company names and roles
        lines = content.split("\n")
        has_company = bool(re.search(r"(?:at|@|,)\s+[A-Z][a-z]+", content))
        has_role = bool(re.search(r"(?:engineer|developer|manager|analyst|director|lead|senior|principal)", content, re.IGNORECASE))

        if not has_company:
            issues.append(ReviewIssue(
                category=ReviewCategory.CONTENT,
                severity=IssueSeverity.HIGH,
                title="Missing company names",
                description="Company names not clearly identifiable",
                suggestion="Format as 'Role at Company' or 'Company - Role' for each position",
            ))
        else:
            strengths.append("Company names present")

        if not has_role:
            issues.append(ReviewIssue(
                category=ReviewCategory.CONTENT,
                severity=IssueSeverity.HIGH,
                title="Missing job titles",
                description="Professional titles not clearly stated",
                suggestion="Include clear job titles for each position",
            ))

        # Check for dates
        date_pattern = r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{4}|\d{1,2}/\d{4}|\d{4}\s*[-–]\s*\d{4}|\d{4}\s*[-–]\s*(?:present|current)"
        if not re.search(date_pattern, content, re.IGNORECASE):
            issues.append(ReviewIssue(
                category=ReviewCategory.CONTENT,
                severity=IssueSeverity.HIGH,
                title="Missing employment dates",
                description="No clear employment dates found in experience section",
                suggestion="Add month/year for each position (e.g., 'Jan 2022 - Present')",
            ))

        # Check for bullet points
        bullets = re.findall(r"^[\s]*[•\-\*]\s+", content, re.MULTILINE)
        if len(bullets) < 3:
            issues.append(ReviewIssue(
                category=ReviewCategory.STRUCTURE,
                severity=IssueSeverity.MEDIUM,
                title="Insufficient bullet points",
                description=f"Only {len(bullets)} bullet points. Use 3-6 per role to detail achievements.",
                suggestion="Add 3-6 bullet points per role focusing on achievements with metrics",
            ))
        else:
            strengths.append(f"Good use of {len(bullets)} bullet points")

        # Check for action verbs
        action_count = self._count_action_verbs(content)
        if action_count < 5:
            issues.append(ReviewIssue(
                category=ReviewCategory.IMPACT,
                severity=IssueSeverity.MEDIUM,
                title="Insufficient action verbs",
                description=f"Only {action_count} strong action verbs found",
                suggestion="Start each bullet with strong action verbs: achieved, built, led, optimized, delivered, etc.",
            ))

        # Check for quantifiable achievements
        quantifiable = len(re.findall(r"\d+%|\$\d+|\d+\s*(?:years?|months?|team|people|users?)", content, re.IGNORECASE))
        if quantifiable < 3:
            suggestions.append("Add quantifiable metrics: percentages, dollar amounts, team sizes, timeframes")
        else:
            strengths.append(f"Good use of {quantifiable} quantifiable metrics")

        # Check for weak phrases
        weak_found = [wp for wp in self.weak_phrases if wp in content.lower()]
        if weak_found:
            issues.append(ReviewIssue(
                category=ReviewCategory.IMPACT,
                severity=IssueSeverity.MEDIUM,
                title="Weak passive language detected",
                description=f"Found weak phrases: {', '.join(weak_found[:3])}",
                suggestion="Replace with strong action verbs. E.g., 'responsible for' → 'managed', 'worked on' → 'developed'",
                examples=weak_found[:3],
            ))

        score = max(0, 100 - len(issues) * 15 - len(suggestions) * 5)
        return SectionReview("experience", score, issues, strengths, suggestions)

    def _review_education(self, content: str) -> SectionReview:
        """Review education section."""
        issues = []
        strengths = []
        suggestions = []

        degree_patterns = [r"\b(?:bachelor|master|phd|doctorate|associate|b\.?s\.?|m\.?s\.?|ph\.?d\.?|b\.?a\.?|m\.?a\.?|mba)\b"]
        has_degree = any(re.search(p, content, re.IGNORECASE) for p in degree_patterns)

        if not has_degree:
            issues.append(ReviewIssue(
                category=ReviewCategory.CONTENT,
                severity=IssueSeverity.MEDIUM,
                title="Degree not clearly stated",
                description="No standard degree abbreviation found",
                suggestion="Include degree with standard abbreviation (BS, MS, PhD, MBA, etc.)",
            ))
        else:
            strengths.append("Degree clearly stated")

        # Check for graduation year
        if not re.search(r"\b20\d{2}\b|\b19\d{2}\b", content):
            suggestions.append("Add graduation year")

        # Check for honors/GPA
        if re.search(r"(?:honors?|dean's list|magna|summa|cum laude|gpa\s*[:=]\s*3\.[5-9])", content, re.IGNORECASE):
            strengths.append("Academic honors mentioned")

        score = 85 if has_degree else 50
        return SectionReview("education", score, issues, strengths, suggestions)

    def _review_skills(self, content: str) -> SectionReview:
        """Review skills section."""
        issues = []
        strengths = []
        suggestions = []

        # Count skills
        skill_items = re.split(r"[,;|/\n]", content)
        skill_count = len([s for s in skill_items if len(s.strip()) > 1])

        if skill_count < 5:
            issues.append(ReviewIssue(
                category=ReviewCategory.CONTENT,
                severity=IssueSeverity.HIGH,
                title="Too few skills listed",
                description=f"Only {skill_count} skills identified. ATS expects 10+ relevant skills.",
                suggestion="Add 10-20 relevant skills including languages, frameworks, tools, and methodologies",
            ))
        elif skill_count > 30:
            issues.append(ReviewIssue(
                category=ReviewCategory.CONTENT,
                severity=IssueSeverity.MEDIUM,
                title="Too many skills listed",
                description=f"{skill_count} skills may dilute focus",
                suggestion="Focus on 10-20 most relevant skills for your target role",
            ))
        else:
            strengths.append(f"Good skill count: {skill_count} skills")

        # Check for categorization
        categories = ["languages", "frameworks", "databases", "cloud", "tools", "methodologies", "libraries"]
        has_categories = any(cat in content.lower() for cat in categories)
        if not has_categories:
            suggestions.append("Group skills by category: Languages, Frameworks, Databases, Cloud, Tools, Methodologies")
        else:
            strengths.append("Skills well-categorized")

        score = max(0, 100 - len(issues) * 20 - len(suggestions) * 5)
        return SectionReview("skills", score, issues, strengths, suggestions)

    def _review_projects(self, content: str) -> SectionReview:
        """Review projects section."""
        issues = []
        strengths = []
        suggestions = []

        if not content or len(content) < 50:
            return SectionReview("projects", 0, [
                ReviewIssue(
                    category=ReviewCategory.CONTENT,
                    severity=IssueSeverity.MEDIUM,
                    title="Missing projects section",
                    description="No projects listed",
                    suggestion="Add 2-3 relevant projects with technologies used and outcomes",
                )
            ], [], ["Add projects to demonstrate practical application of skills"])

        # Check for project details
        project_indicators = ["github", "demo", "deployed", "built", "created", "developed"]
        has_details = sum(1 for ind in project_indicators if ind in content.lower())

        if has_details < 2:
            suggestions.append("Add project links (GitHub, live demo), technologies used, and your specific contributions")

        score = min(100, 50 + len(content) // 10)
        return SectionReview("projects", score, issues, strengths, suggestions)

    def _review_certifications(self, content: str) -> SectionReview:
        """Review certifications section."""
        issues = []
        strengths = []
        suggestions = []

        if not content or len(content) < 10:
            return SectionReview("certifications", 50, [], [], [
                "Consider adding relevant certifications for your target role",
                "Include certification name, issuing organization, and date"
            ])

        strengths.append("Certifications included")
        return SectionReview("certifications", 80, [], strengths, suggestions)

    def _review_generic(self, section_name: str, content: str) -> SectionReview:
        """Generic section review."""
        word_count = len(content.split())
        if word_count < 20:
            return SectionReview(section_name, 30, [
                ReviewIssue(
                    category=ReviewCategory.CONTENT,
                    severity=IssueSeverity.MEDIUM,
                    title=f"Section '{section_name}' is too brief",
                    description=f"Only {word_count} words",
                    suggestion=f"Expand {section_name} with more relevant details",
                )
            ], [], [f"Add more detail to {section_name}"])

        return SectionReview(section_name, 70, [], [f"{section_name} present"], ["Consider adding more detail"])

    def _count_action_verbs(self, content: str) -> int:
        """Count strong action verbs in content."""
        content_lower = content.lower()
        count = 0
        for category, verbs in self.action_verbs.items():
            for verb in verbs:
                if re.search(rf"\b{verb}\b", content_lower):
                    count += 1
        return count

    def _calculate_overall_score(self, sections: Dict[str, SectionReview]) -> float:
        """Calculate weighted overall score."""
        weights = {
            "summary": 0.15,
            "experience": 0.40,
            "education": 0.10,
            "skills": 0.20,
            "projects": 0.10,
            "certifications": 0.05,
        }

        total = 0
        total_weight = 0
        for section, weight in weights.items():
            if section in sections:
                total += sections[section].score * weight
                total_weight += weight

        return total / total_weight if total_weight > 0 else 0

    def _score_to_grade(self, score: float) -> str:
        """Convert score to letter grade."""
        if score >= 97: return "A+"
        elif score >= 93: return "A"
        elif score >= 90: return "A-"
        elif score >= 87: return "B+"
        elif score >= 83: return "B"
        elif score >= 80: return "B-"
        elif score >= 77: return "C+"
        elif score >= 73: return "C"
        elif score >= 70: return "C-"
        elif score >= 67: return "D+"
        elif score >= 63: return "D"
        elif score >= 60: return "D-"
        else: return "F"

    def _identify_priorities(self, sections: Dict[str, SectionReview]) -> List[str]:
        """Identify top 3 priorities for improvement."""
        priorities = []

        # Collect all high/critical issues
        all_issues = []
        for section in sections.values():
            for issue in section.issues:
                if issue.severity in [IssueSeverity.CRITICAL, IssueSeverity.HIGH]:
                    priorities.append(f"{issue.section}: {issue.title}")

        return priorities[:3] if priorities else ["Review all sections for completeness", "Add quantifiable achievements", "Optimize for target role keywords"]

    def _collect_strengths(self, sections: Dict[str, SectionReview]) -> List[str]:
        """Collect all strengths across sections."""
        strengths = []
        for section in sections.values():
            strengths.extend(section.strengths)
        return strengths[:10]

    def _generate_overall_feedback(self, score: float, sections: Dict[str, SectionReview]) -> str:
        """Generate overall feedback summary."""
        if score >= 90:
            return "Excellent resume! Strong structure, content, and impact. Minor polish needed."
        elif score >= 80:
            return "Good resume with solid foundation. Some sections need more impact and quantification."
        elif score >= 70:
            return "Decent foundation but needs significant improvement in achievements, keywords, and formatting."
        elif score >= 60:
            return "Resume needs significant restructuring. Focus on achievements, keywords, and formatting."
        else:
            return "Resume requires major revision. Consider professional resume review service."

    def _create_improvement_plan(self, sections: Dict[str, SectionReview]) -> List[Dict[str, Any]]:
        """Create prioritized improvement plan."""
        plan = []

        # Priority 1: Critical issues
        for section_name, section in sections.items():
            for issue in section.issues:
                if issue.severity == IssueSeverity.CRITICAL:
                    plan.append({
                        "priority": 1,
                        "section": issue.section,
                        "action": issue.suggestion,
                        "effort": "high",
                        "impact": "critical",
                    })

        # Priority 2: High severity
        for section_name, section in sections.items():
            for issue in section.issues:
                if issue.severity == IssueSeverity.HIGH:
                    plan.append({
                        "priority": 2,
                        "section": issue.section,
                        "action": issue.suggestion,
                        "effort": "medium",
                        "impact": "high",
                    })

        # Priority 3: Suggestions
        for section_name, section in sections.items():
            for suggestion in section.suggestions:
                plan.append({
                    "priority": 3,
                    "section": section_name,
                    "action": suggestion,
                    "effort": "low",
                    "impact": "medium",
                })

        return plan[:10]


from typing import Optional