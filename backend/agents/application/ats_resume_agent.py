import logging
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum as PyEnum

logger = logging.getLogger(__name__)


class ATSIssueType(str, PyEnum):
    MISSING_KEYWORDS = "missing_keywords"
    FORMATTING = "formatting"
    SECTIONS = "sections"
    CONTACT_INFO = "contact_info"
    EXPERIENCE = "experience"
    EDUCATION = "education"
    SKILLS = "skills"
    ACHIEVEMENTS = "achievements"
    LENGTH = "length"
    FILE_FORMAT = "file_format"


class ATSIssueSeverity(str, PyEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class ATSIssue:
    """An issue found during ATS analysis."""
    type: ATSIssueType
    severity: ATSIssueSeverity
    title: str
    description: str
    suggestion: str
    location: Optional[str] = None  # Section or line reference

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value if hasattr(self.type, "value") else str(self.type),
            "severity": self.severity.value if hasattr(self.severity, "value") else str(self.severity),
            "title": self.title,
            "description": self.description,
            "suggestion": self.suggestion,
            "location": self.location,
        }


@dataclass
class ATSAnalysisResult:
    """Complete ATS analysis result."""
    overall_score: float  # 0-100
    passed: bool
    issues: List[ATSIssue]
    keyword_match_score: float
    format_score: float
    section_score: float
    content_score: float
    missing_keywords: List[str]
    matched_keywords: List[str]
    recommendations: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_score": self.overall_score,
            "passed": self.passed,
            "issues": [i.to_dict() for i in self.issues],
            "keyword_match_score": self.keyword_match_score,
            "format_score": self.format_score,
            "section_score": self.section_score,
            "content_score": self.content_score,
            "missing_keywords": self.missing_keywords,
            "matched_keywords": self.matched_keywords,
            "recommendations": self.recommendations,
        }


class ATSResumeAgent:
    """Analyze resume for ATS (Applicant Tracking System) compatibility."""

    def __init__(self):
        self.name = "ats_resume_agent"

        # Common ATS-friendly section headers
        self.standard_sections = {
            "contact": ["contact", "contact information", "personal information"],
            "summary": ["summary", "professional summary", "profile", "objective", "about me"],
            "experience": ["experience", "work experience", "employment history", "professional experience", "work history"],
            "education": ["education", "academic background", "qualifications", "degrees"],
            "skills": ["skills", "technical skills", "core competencies", "expertise", "technologies"],
            "projects": ["projects", "key projects", "personal projects", "portfolio"],
            "certifications": ["certifications", "certificates", "licenses", "credentials"],
            "achievements": ["achievements", "awards", "honors", "accomplishments"],
            "publications": ["publications", "papers", "research"],
            "languages": ["languages", "language proficiency"],
            "volunteer": ["volunteer", "volunteer experience", "community involvement"],
        }

        # Required contact fields
        self.required_contact = ["email", "phone", "location"]

        # ATS-friendly keywords by role category
        self.role_keywords = {
            "software engineer": [
                "python", "java", "javascript", "typescript", "c++", "go", "rust",
                "react", "vue", "angular", "node.js", "django", "flask", "fastapi", "spring",
                "sql", "nosql", "postgresql", "mongodb", "redis", "elasticsearch",
                "aws", "gcp", "azure", "docker", "kubernetes", "terraform",
                "git", "ci/cd", "jenkins", "github actions", "gitlab ci",
                "microservices", "rest", "graphql", "grpc", "api",
                "testing", "jest", "pytest", "cypress", "tdd",
                "agile", "scrum", "kanban", "jira", "confluence",
            ],
            "data scientist": [
                "python", "r", "sql", "pandas", "numpy", "scikit-learn", "tensorflow", "pytorch",
                "machine learning", "deep learning", "nlp", "computer vision",
                "statistics", "probability", "hypothesis testing", "a/b testing",
                "data visualization", "tableau", "power bi", "matplotlib", "seaborn",
                "spark", "hadoop", "kafka", "airflow", "mlops",
                "feature engineering", "model deployment", "model monitoring",
            ],
            "devops engineer": [
                "aws", "gcp", "azure", "docker", "kubernetes", "terraform", "ansible",
                "ci/cd", "jenkins", "github actions", "gitlab ci", "argo cd",
                "linux", "bash", "python", "go", "monitoring", "prometheus", "grafana",
                "elk", "logging", "observability", "sre", "incident response",
                "helm", "istio", "service mesh", "argocd", "flux",
            ],
            "product manager": [
                "product strategy", "roadmap", "prioritization", "user research",
                "analytics", "metrics", "kpis", "okrs", "stakeholder management",
                "agile", "scrum", "kanban", "jira", "confluence",
                "wireframing", "figma", "prototyping", "user stories",
                "go-to-market", "pricing", "competitive analysis",
            ],
        }

    def analyze(
        self,
        resume_text: str,
        target_role: Optional[str] = None,
        job_description: Optional[str] = None,
    ) -> ATSAnalysisResult:
        """Analyze resume for ATS compatibility."""
        logger.info(f"Analyzing resume for ATS (target: {target_role})")

        # Extract keywords from job description if provided
        jd_keywords = set()
        if job_description:
            jd_keywords = self._extract_keywords(job_description)

        # Use target role keywords if no JD
        role_keywords = set()
        if target_role and not job_description:
            role_keywords = set(self.role_keywords.get(target_role.lower(), []))

        # Combine keywords
        target_keywords = jd_keywords | role_keywords

        # Run analyses
        issues = []
        issues.extend(self._check_sections(resume_text))
        issues.extend(self._check_contact_info(resume_text))
        issues.extend(self._check_formatting(resume_text))
        issues.extend(self._check_experience(resume_text))
        issues.extend(self._check_education(resume_text))
        issues.extend(self._check_skills(resume_text))
        issues.extend(self._check_length(resume_text))
        issues.extend(self._check_achievements(resume_text))

        # Keyword analysis
        keyword_result = self._analyze_keywords(resume_text, target_keywords)

        # Calculate scores
        keyword_score = keyword_result["match_percentage"]
        format_score = self._calculate_format_score(issues)
        section_score = self._calculate_section_score(issues)
        content_score = self._calculate_content_score(issues)

        overall_score = (
            keyword_score * 0.35 +
            format_score * 0.20 +
            section_score * 0.20 +
            content_score * 0.25
        )

        passed = overall_score >= 70

        # Generate recommendations
        recommendations = self._generate_recommendations(issues, keyword_result, target_role)

        return ATSAnalysisResult(
            overall_score=round(overall_score, 1),
            passed=passed,
            issues=issues,
            keyword_match_score=round(keyword_result["match_percentage"], 1),
            format_score=round(format_score, 1),
            section_score=round(section_score, 1),
            content_score=round(content_score, 1),
            missing_keywords=keyword_result["missing_keywords"],
            matched_keywords=keyword_result["matched_keywords"],
            recommendations=recommendations,
        )

    def _extract_keywords(self, text: str) -> set:
        """Extract technical keywords from text."""
        tech_keywords = [
            "python", "java", "javascript", "typescript", "c++", "c#", "go", "rust",
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

        text_lower = text.lower()
        found = set()
        for kw in tech_keywords:
            if re.search(rf"\b{re.escape(kw)}\b", text_lower):
                found.add(kw)
        return found

    def _check_sections(self, text: str) -> List[ATSIssue]:
        """Check for standard resume sections."""
        issues = []
        text_lower = text.lower()

        found_sections = {}
        missing_sections = []

        for section, variants in self.standard_sections.items():
            found = False
            for variant in variants:
                if re.search(rf"\b{variant}\b", text_lower):
                    found = True
                    found_sections[section] = variant
                    break
            if not found and section in ["contact", "experience", "education", "skills"]:
                missing_sections.append(section)

        if missing_sections:
            issues.append(ATSIssue(
                type=ATSIssueType.SECTIONS,
                severity=ATSIssueSeverity.HIGH,
                title=f"Missing critical sections: {', '.join(missing_sections)}",
                description=f"ATS systems expect standard sections. Missing: {', '.join(missing_sections)}",
                suggestion=f"Add the following sections with standard headers: {', '.join(missing_sections)}",
            ))

        # Check for non-standard section names
        for section, found_variant in found_sections.items():
            standard = self.standard_sections[section][0]
            if found_variant.lower() != standard:
                issues.append(ATSIssue(
                    type=ATSIssueType.SECTIONS,
                    severity=ATSIssueSeverity.INFO,
                    title=f"Non-standard section name: '{found_variant}'",
                    description=f"Section '{found_variant}' may not be recognized by ATS. Standard is '{standard}'.",
                    suggestion=f"Consider renaming to standard header: '{standard}'",
                ))

        return issues

    def _check_contact_info(self, text: str) -> List[ATSIssue]:
        """Check for required contact information."""
        issues = []
        text_lower = text.lower()

        # Email
        email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
        if not re.search(email_pattern, text):
            issues.append(ATSIssue(
                type=ATSIssueType.CONTACT_INFO,
                severity=ATSIssueSeverity.CRITICAL,
                title="Missing email address",
                description="No email address found in resume",
                suggestion="Add a professional email address at the top of your resume",
            ))

        # Phone
        phone_pattern = r"(\+\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}"
        if not re.search(phone_pattern, text):
            issues.append(ATSIssue(
                type=ATSIssueType.CONTACT_INFO,
                severity=ATSIssueSeverity.HIGH,
                title="Missing phone number",
                description="No phone number found in resume",
                suggestion="Add a phone number in the contact section",
            ))

        # Location
        location_keywords = ["city", "state", "country", "remote", "relocation"]
        has_location = any(kw in text.lower() for kw in location_keywords)
        if not has_location:
            issues.append(ATSIssue(
                type=ATSIssueType.CONTACT_INFO,
                severity=ATSIssueSeverity.MEDIUM,
                title="Missing location",
                description="No location (city/state/country/remote) found",
                suggestion="Add your location or 'Remote' to the contact section",
            ))

        # LinkedIn
        if "linkedin.com" not in text.lower():
            issues.append(ATSIssue(
                type=ATSIssueType.CONTACT_INFO,
                severity=ATSIssueSeverity.MEDIUM,
                title="Missing LinkedIn profile",
                description="No LinkedIn URL found",
                suggestion="Add your LinkedIn profile URL to the contact section",
            ))

        # GitHub/Portfolio
        if "github.com" not in text.lower() and "portfolio" not in text.lower():
            issues.append(ATSIssue(
                type=ATSIssueType.CONTACT_INFO,
                severity=ATSIssueSeverity.LOW,
                title="Missing GitHub/portfolio",
                description="No GitHub or portfolio link found",
                suggestion="Add GitHub or portfolio URL to showcase your work",
            ))

        return issues

    def _check_formatting(self, text: str) -> List[ATSIssue]:
        """Check resume formatting for ATS compatibility."""
        issues = []

        # Check for tables (approximate)
        if "|" in text and text.count("|") > 10:
            issues.append(ATSIssue(
                type=ATSIssueType.FORMATTING,
                severity=ATSIssueSeverity.HIGH,
                title="Possible table formatting detected",
                description="Tables may not parse correctly in ATS systems",
                suggestion="Avoid tables. Use simple text with clear section headers and bullet points instead.",
            ))

        # Check for columns (approximate - lots of whitespace patterns)
        lines = text.split("\n")
        multi_col_lines = sum(1 for line in lines if len(line) > 100 and line.count("  ") > 5)
        if multi_col_lines > len(lines) * 0.3:
            issues.append(ATSIssue(
                type=ATSIssueType.FORMATTING,
                severity=ATSIssueSeverity.MEDIUM,
                title="Possible multi-column layout",
                description="Multi-column layouts may not parse correctly in ATS",
                suggestion="Use single-column layout with clear section breaks",
            ))

        # Check for special characters that might cause issues
        special_chars = ["\u2605", "\u2586", "\u25cf", "\u25a0", "\u25ba", "\u25bc", "\u2666", "\u2713", "\u2714"]
        for char in special_chars:
            if char in text:
                issues.append(ATSIssue(
                    type=ATSIssueType.FORMATTING,
                    severity=ATSIssueSeverity.LOW,
                    title=f"Special character detected: '{char}'",
                    description=f"Special characters like '{char}' may not render correctly in ATS",
                    suggestion=f"Replace '{char}' with standard bullet points (- or *) or plain text",
                ))
                break  # Only report once

        # Check for headers/footers (repeated text at top/bottom)
        lines = text.split("\n")
        if len(lines) > 5:
            first_lines = "\n".join(lines[:3]).lower()
            last_lines = "\n".join(lines[-3:]).lower()
            if first_lines == last_lines:
                issues.append(ATSIssue(
                    type=ATSIssueType.FORMATTING,
                    severity=ATSIssueSeverity.MEDIUM,
                    title="Possible header/footer content in body",
                    description="Repeated content at top and bottom may indicate header/footer in body text",
                    suggestion="Remove header/footer content from resume body; ATS may parse it as part of content",
                ))

        return issues

    def _check_experience(self, text: str) -> List[ATSIssue]:
        """Check experience section quality."""
        issues = []

        # Check for dates
        date_patterns = [
            r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{4}\b",
            r"\b\d{1,2}/\d{4}\b",
            r"\b\d{4}\s*[--]\s*\d{4}\b",
            r"\b\d{4}\s*[--]\s*(?:present|current)\b",
        ]

        has_dates = any(re.search(p, text, re.IGNORECASE) for p in date_patterns)
        if not has_dates:
            issues.append(ATSIssue(
                type=ATSIssueType.EXPERIENCE,
                severity=ATSIssueSeverity.HIGH,
                title="Missing employment dates",
                description="No clear employment dates found in experience section",
                suggestion="Add start and end dates (month/year) for each position",
            ))

        # Check for bullet points
        bullet_count = len(re.findall(r"^[\s]*[*\-\*]\s+", text, re.MULTILINE))
        if bullet_count < 3:
            issues.append(ATSIssue(
                type=ATSIssueType.EXPERIENCE,
                severity=ATSIssueSeverity.MEDIUM,
                title="Insufficient bullet points in experience",
                description=f"Only {bullet_count} bullet points found. ATS expects detailed accomplishments.",
                suggestion="Add 3-6 bullet points per role describing achievements with metrics",
            ))

        # Check for action verbs
        action_verbs = [
            "achieved", "built", "created", "developed", "designed", "implemented",
            "improved", "increased", "led", "managed", "optimized", "reduced",
            "delivered", "launched", "automated", "architected", "engineered",
            "spearheaded", "orchestrated", "transformed", "streamlined",
        ]
        text_lower = text.lower()
        verb_count = sum(1 for verb in action_verbs if re.search(rf"\b{verb}\b", text_lower))
        if verb_count < 5:
            issues.append(ATSIssue(
                type=ATSIssueType.EXPERIENCE,
                severity=ATSIssueSeverity.MEDIUM,
                title="Insufficient action verbs",
                description=f"Only {verb_count} strong action verbs found. Use more powerful verbs to describe achievements.",
                suggestion="Start bullet points with strong action verbs: achieved, built, led, optimized, delivered, etc.",
            ))

        # Check for quantifiable achievements
        quantifiable_patterns = [
            r"\d+%",
            r"\$\d+",
            r"\d+\s*(?:years?|months?)",
            r"\d+\s*(?:team|people|users?|customers?)",
            r"(?:increased|decreased|improved|reduced)\s+\d+",
        ]
        quantifiable_count = sum(len(re.findall(p, text, re.IGNORECASE)) for p in quantifiable_patterns)
        if quantifiable_count < 3:
            issues.append(ATSIssue(
                type=ATSIssueType.ACHIEVEMENTS,
                severity=ATSIssueSeverity.MEDIUM,
                title="Insufficient quantifiable achievements",
                description=f"Only {quantifiable_count} quantifiable metrics found. ATS and recruiters look for measurable impact.",
                suggestion="Add specific numbers: percentages, dollar amounts, team sizes, time savings, etc.",
            ))

        return issues

    def _check_education(self, text: str) -> List[ATSIssue]:
        """Check education section."""
        issues = []

        # Check for degree
        degree_patterns = [
            r"\b(?:bachelor|master|phd|doctorate|associate|b\.?s\.?|m\.?s\.?|ph\.?d\.?|b\.?a\.?|m\.?a\.?)\b",
        ]
        has_degree = any(re.search(p, text, re.IGNORECASE) for p in degree_patterns)

        if not has_degree:
            issues.append(ATSIssue(
                type=ATSIssueType.EDUCATION,
                severity=ATSIssueSeverity.LOW,
                title="No degree found",
                description="No degree abbreviation found in education section",
                suggestion="Add your degree(s) with standard abbreviations (BS, MS, PhD, etc.)",
            ))

        return issues

    def _check_skills(self, text: str) -> List[ATSIssue]:
        """Check skills section."""
        issues = []

        # Check for skills section
        skills_keywords = ["skills", "technologies", "technical skills", "core competencies", "expertise"]
        has_skills_section = any(kw in text.lower() for kw in skills_keywords)

        if not has_skills_section:
            issues.append(ATSIssue(
                type=ATSIssueType.SKILLS,
                severity=ATSIssueSeverity.HIGH,
                title="Missing skills section",
                description="No dedicated skills section found",
                suggestion="Add a dedicated 'Skills' or 'Technical Skills' section listing relevant technologies",
            ))

        # Check for skill categorization
        categories = ["languages", "frameworks", "databases", "cloud", "tools", "methodologies"]
        has_categories = any(cat in text.lower() for cat in categories)

        if not has_categories and len(text) > 500:
            issues.append(ATSIssue(
                type=ATSIssueType.SKILLS,
                severity=ATSIssueSeverity.INFO,
                title="Skills not categorized",
                description="Skills listed without categorization",
                suggestion="Group skills by category (Languages, Frameworks, Databases, Cloud, Tools, etc.) for better readability",
            ))

        return issues

    def _check_length(self, text: str) -> List[ATSIssue]:
        """Check resume length."""
        issues = []
        word_count = len(text.split())

        if word_count < 300:
            issues.append(ATSIssue(
                type=ATSIssueType.LENGTH,
                severity=ATSIssueSeverity.MEDIUM,
                title="Resume too short",
                description=f"Only {word_count} words. Resume may lack sufficient detail.",
                suggestion="Expand on experience, projects, and skills. Aim for 400-800 words for most roles.",
            ))
        elif word_count > 1000:
            issues.append(ATSIssue(
                type=ATSIssueType.LENGTH,
                severity=ATSIssueSeverity.MEDIUM,
                title="Resume too long",
                description=f"{word_count} words exceeds recommended length for most roles.",
                suggestion="Condense to 1-2 pages. Focus on recent, relevant experience. Remove outdated information.",
            ))

        return issues


    def _check_achievements(self, text: str) -> List[ATSIssue]:
        """Check for achievements/awards section."""
        issues = []

        achievement_keywords = ["achievements", "awards", "honors", "accomplishments", "recognitions"]
        has_achievements = any(kw in text.lower() for kw in achievement_keywords)

        if not has_achievements:
            issues.append(ATSIssue(
                type=ATSIssueType.ACHIEVEMENTS,
                severity=ATSIssueSeverity.INFO,
                title="No achievements section",
                description="No dedicated achievements/awards section found",
                suggestion="Consider adding an 'Achievements' or 'Awards' section to highlight recognition",
            ))

        return issues

    def _analyze_keywords(self, text: str, target_keywords: set) -> Dict[str, Any]:
        """Analyze keyword matching."""
        if not target_keywords:
            return {
                "match_percentage": 100,
                "matched_keywords": [],
                "missing_keywords": [],
            }

        text_lower = text.lower()
        matched = []
        missing = []

        for kw in target_keywords:
            if re.search(rf"\b{re.escape(kw)}\b", text.lower()):
                matched.append(kw)
            else:
                missing.append(kw)

        match_pct = (len(matched) / len(target_keywords) * 100) if target_keywords else 100

        return {
            "match_percentage": round(match_pct, 1),
            "matched_keywords": matched,
            "missing_keywords": missing,
        }

    def _calculate_format_score(self, issues: List[ATSIssue]) -> float:
        """Calculate formatting score."""
        format_issues = [i for i in issues if i.type == ATSIssueType.FORMATTING]
        critical = sum(1 for i in format_issues if i.severity == ATSIssueSeverity.CRITICAL)
        high = sum(1 for i in format_issues if i.severity == ATSIssueSeverity.HIGH)
        medium = sum(1 for i in format_issues if i.severity == ATSIssueSeverity.MEDIUM)
        low = sum(1 for i in format_issues if i.severity == ATSIssueSeverity.LOW)

        penalty = critical * 25 + high * 15 + medium * 8 + low * 3
        return max(0, 100 - penalty)

    def _calculate_section_score(self, issues: List[ATSIssue]) -> float:
        """Calculate section completeness score."""
        section_issues = [i for i in issues if i.type == ATSIssueType.SECTIONS]
        critical = sum(1 for i in section_issues if i.severity == ATSIssueSeverity.CRITICAL)
        high = sum(1 for i in section_issues if i.severity == ATSIssueSeverity.HIGH)
        medium = sum(1 for i in section_issues if i.severity == ATSIssueSeverity.MEDIUM)

        penalty = critical * 30 + high * 20 + medium * 10
        return max(0, 100 - penalty)

    def _calculate_content_score(self, issues: List[ATSIssue]) -> float:
        """Calculate content quality score."""
        content_types = [ATSIssueType.EXPERIENCE, ATSIssueType.ACHIEVEMENTS, ATSIssueType.SKILLS, ATSIssueType.EDUCATION]
        content_issues = [i for i in issues if i.type in content_types]

        critical = sum(1 for i in content_issues if i.severity == ATSIssueSeverity.CRITICAL)
        high = sum(1 for i in content_issues if i.severity == ATSIssueSeverity.HIGH)
        medium = sum(1 for i in content_issues if i.severity == ATSIssueSeverity.MEDIUM)
        low = sum(1 for i in content_issues if i.severity == ATSIssueSeverity.LOW)
        info = sum(1 for i in content_issues if i.severity == ATSIssueSeverity.INFO)

        penalty = critical * 20 + high * 15 + medium * 10 + low * 5 + info * 2
        return max(0, 100 - penalty)

    def _generate_recommendations(
        self,
        issues: List[ATSIssue],
        keyword_result: Dict[str, Any],
        target_role: Optional[str],
    ) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []

        # Critical issues first
        critical = [i for i in issues if i.severity == ATSIssueSeverity.CRITICAL]
        for issue in critical:
            recommendations.append(f"CRITICAL: {issue.suggestion}")

        # High severity
        high = [i for i in issues if i.severity == ATSIssueSeverity.HIGH]
        for issue in high[:3]:
            recommendations.append(issue.suggestion)

        # Keyword recommendations
        if keyword_result["missing_keywords"]:
            top_missing = keyword_result["missing_keywords"][:5]
            recommendations.append(f"Add missing keywords for {target_role or 'target role'}: {', '.join(top_missing)}")

        # General recommendations
        recommendations.extend([
            "Use standard section headers (Experience, Education, Skills, Projects)",
            "Use bullet points with strong action verbs for experience",
            "Quantify achievements with specific metrics (%, $, numbers)",
            "Include a dedicated Skills section categorized by type",
            "Keep resume to 1-2 pages with 400-800 words",
            "Use standard fonts (Arial, Calibri, Helvetica) and avoid graphics",
            "Save as PDF with selectable text (not scanned image)",
            "Test resume with free ATS scanner tools before applying",
        ])

        return recommendations[:10]


from typing import Optional