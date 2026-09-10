import logging
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum as PyEnum

logger = logging.getLogger(__name__)


class QuestionType(str, PyEnum):
    BEHAVIORAL = "behavioral"
    TECHNICAL = "technical"
    SITUATIONAL = "situational"
    EXPERIENCE = "experience"
    MOTIVATION = "motivation"
    SALARY = "salary"
    AVAILABILITY = "availability"
    CULTURE_FIT = "culture_fit"


class AnswerStrategy(str, PyEnum):
    STAR = "star"           # Situation, Task, Action, Result
    CAR = "car"             # Challenge, Action, Result
    PAR = "par"             # Problem, Action, Result
    DIRECT = "direct"       # Direct factual answer
    NARRATIVE = "narrative" # Story-based answer


@dataclass
class ApplicationQuestion:
    """An application question."""
    question: str
    question_type: QuestionType
    required: bool = True
    max_length: Optional[int] = None
    keywords: List[str] = field(default_factory=list)
    context: Optional[str] = None


@dataclass
class AnswerDraft:
    """A draft answer to an application question."""
    question: str
    question_type: QuestionType
    answer: str
    strategy: AnswerStrategy
    word_count: int
    key_points: List[str]
    confidence: float  # 0-100
    suggestions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "question": self.question,
            "question_type": self.question_type.value if hasattr(self.question_type, "value") else str(self.question_type),
            "answer": self.answer,
            "strategy": self.strategy.value if hasattr(self.strategy, "value") else str(self.strategy),
            "word_count": self.word_count,
            "key_points": self.key_points,
            "confidence": self.confidence,
            "suggestions": self.suggestions,
        }


@dataclass
class ApplicationAnswersResult:
    """Complete set of answers for an application."""
    answers: List[AnswerDraft]
    overall_confidence: float
    total_word_count: int
    missing_required: List[str]
    review_notes: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "answers": [a.to_dict() for a in self.answers],
            "overall_confidence": self.overall_confidence,
            "total_word_count": self.total_word_count,
            "missing_required": self.missing_required,
            "review_notes": self.review_notes,
        }


class ApplicationAnswerAgent:
    """Generate and optimize answers to application questions."""

    def __init__(self):
        self.name = "application_answer_agent"

        # Question patterns by type
        self.question_patterns = {
            QuestionType.BEHAVIORAL: [
                r"tell me about a time",
                r"describe a situation",
                r"give an example",
                r"how did you handle",
                r"walk me through",
            ],
            QuestionType.SITUATIONAL: [
                r"what would you do if",
                r"how would you handle",
                r"imagine a scenario",
                r"suppose you",
            ],
            QuestionType.TECHNICAL: [
                r"how would you implement",
                r"explain the difference",
                r"what is your approach to",
                r"design a system",
                r"optimize",
                r"debug",
            ],
            QuestionType.EXPERIENCE: [
                r"describe your experience",
                r"what is your experience with",
                r"how many years",
                r"walk me through your",
            ],
            QuestionType.MOTIVATION: [
                r"why do you want",
                r"why are you interested",
                r"what attracts you",
                r"why this company",
                r"why this role",
            ],
            QuestionType.SALARY: [
                r"salary expectation",
                r"compensation expectation",
                r"desired salary",
                r"compensation range",
            ],
            QuestionType.AVAILABILITY: [
                r"when can you start",
                r"notice period",
                r"available to start",
            ],
            QuestionType.CULTURE_FIT: [
                r"how do you work",
                r"team environment",
                r"work style",
                r"values",
                r"mission",
            ],
        }

        # STAR templates
        self.star_templates = {
            "leadership": "Situation: {situation}\nTask: {task}\nAction: {action}\nResult: {result}",
            "conflict_resolution": "Situation: {situation}\nTask: {task}\nAction: {action}\nResult: {result}",
            "problem_solving": "Situation: {situation}\nTask: {task}\nAction: {action}\nResult: {result}",
            "failure_learning": "Situation: {situation}\nTask: {task}\nAction: {action}\nResult: {result}",
            "project_success": "Situation: {situation}\nTask: {task}\nAction: {action}\nResult: {result}",
        }

        # Common question templates
        self.common_questions = {
            "tell_me_about_yourself": {
                "type": QuestionType.EXPERIENCE,
                "template": "I'm a {current_role} with {years} years of experience in {key_skills}. I've {key_achievement}. Currently, I'm looking for {target_role} where I can {career_goal}.",
            },
            "why_this_company": {
                "type": QuestionType.MOTIVATION,
                "template": "I've followed {company}'s work in {domain} and admire {specific_achievement}. Your {value} aligns with my {personal_value}. I want to contribute to {company_mission}.",
            },
            "why_this_role": {
                "type": QuestionType.MOTIVATION,
                "template": "This role combines my expertise in {skill_1} and {skill_2} with my passion for {domain}. I've {relevant_experience} and want to {career_goal}.",
            },
            "greatest_achievement": {
                "type": QuestionType.BEHAVIORAL,
                "template": "In my role as {role}, I {situation}. My task was {task}. I {action} which resulted in {result}. This taught me {lesson}.",
            },
            "challenge_overcome": {
                "type": QuestionType.BEHAVIORAL,
                "template": "We faced {challenge}. I {action} by {specific_action}. The result was {result}. This experience taught me {lesson}.",
            },
            "conflict_resolution": {
                "type": QuestionType.BEHAVIORAL,
                "template": "There was disagreement about {topic}. I {action} by {specific_action}. The outcome was {result}. I learned {lesson}.",
            },
            "weakness": {
                "type": QuestionType.BEHAVIORAL,
                "template": "An area I'm improving is {weakness}. I've been working on it by {action}. I've seen progress in {evidence}.",
            },
            "salary_expectation": {
                "type": QuestionType.SALARY,
                "template": "Based on my {years} years of experience in {role} and market research for {location}, I'm targeting {range}. I'm flexible based on total compensation.",
            },
            "why_leaving": {
                "type": QuestionType.MOTIVATION,
                "template": "I've learned a lot at {current_company}, but I'm seeking {growth_opportunity} that aligns with my goal of {career_goal}. {company} offers this through {specific_reason}.",
            },
        }

    def generate_answers(
        self,
        questions: List[ApplicationQuestion],
        candidate_profile: Dict[str, Any],
        target_role: Optional[str] = None,
        target_company: Optional[str] = None,
    ) -> ApplicationAnswersResult:
        """Generate answers for a list of application questions."""
        logger.info(f"Generating answers for {len(questions)} questions")

        answers = []
        missing_required = []

        for q in questions:
            if q.required and not q.question.strip():
                missing_required.append(q.question)
                continue

            answer = self._generate_answer(q, candidate_profile, target_role, target_company)
            answers.append(answer)

        overall_confidence = sum(a.confidence for a in answers) / len(answers) if answers else 0
        total_words = sum(a.word_count for a in answers)
        missing = [q.question for q in questions if q.required and not any(a.question == q.question for a in answers)]

        review_notes = self._generate_review_notes(answers, candidate_profile)

        return ApplicationAnswersResult(
            answers=answers,
            overall_confidence=round(overall_confidence, 1),
            total_word_count=total_words,
            missing_required=missing,
            review_notes=review_notes,
        )

    def _generate_answer(
        self,
        question: ApplicationQuestion,
        profile: Dict[str, Any],
        target_role: Optional[str],
        target_company: Optional[str],
    ) -> AnswerDraft:
        """Generate answer for a single question."""
        # Detect question type if not specified
        q_type = question.question_type or self._classify_question(question.question)

        # Select strategy
        strategy = self._select_strategy(q_type, question.question)

        # Generate answer based on type
        if q_type == QuestionType.BEHAVIORAL:
            answer_text = self._generate_behavioral_answer(question, profile)
        elif q_type == QuestionType.SITUATIONAL:
            answer_text = self._generate_situational_answer(question, profile)
        elif q_type == QuestionType.TECHNICAL:
            answer_text = self._generate_technical_answer(question, profile)
        elif q_type == QuestionType.EXPERIENCE:
            answer_text = self._generate_experience_answer(question, profile)
        elif q_type == QuestionType.MOTIVATION:
            answer_text = self._generate_motivation_answer(question, profile, target_company)
        elif q_type == QuestionType.SALARY:
            answer_text = self._generate_salary_answer(question, profile)
        elif q_type == QuestionType.AVAILABILITY:
            answer_text = self._generate_availability_answer(question, profile)
        elif q_type == QuestionType.CULTURE_FIT:
            answer_text = self._generate_culture_fit_answer(question, profile)
        else:
            answer_text = self._generate_generic_answer(question, profile)

        # Calculate metrics
        word_count = len(answer_text.split())
        key_points = self._extract_key_points(answer_text, q_type)
        confidence = self._calculate_confidence(answer_text, question, profile)
        suggestions = self._generate_answer_suggestions(answer_text, question, profile)

        return AnswerDraft(
            question=question.question,
            question_type=q_type,
            answer=answer_text,
            strategy=strategy,
            word_count=word_count,
            key_points=key_points,
            confidence=confidence,
            suggestions=suggestions,
        )

    def _classify_question(self, question: str) -> QuestionType:
        """Classify question type based on keywords."""
        q_lower = question.lower()

        for q_type, patterns in self.question_patterns.items():
            for pattern in patterns:
                if re.search(pattern, q_lower):
                    return q_type

        return QuestionType.EXPERIENCE

    def _select_strategy(self, q_type: QuestionType, question: str) -> AnswerStrategy:
        """Select best answer strategy for question type."""
        if q_type == QuestionType.BEHAVIORAL:
            return AnswerStrategy.STAR
        elif q_type == QuestionType.SITUATIONAL:
            return AnswerStrategy.CAR
        elif q_type == QuestionType.TECHNICAL:
            return AnswerStrategy.DIRECT
        elif q_type == QuestionType.EXPERIENCE:
            return AnswerStrategy.NARRATIVE
        elif q_type == QuestionType.MOTIVATION:
            return AnswerStrategy.DIRECT
        elif q_type == QuestionType.SALARY:
            return AnswerStrategy.DIRECT
        else:
            return AnswerStrategy.DIRECT

    def _generate_behavioral_answer(self, question: ApplicationQuestion, profile: Dict) -> str:
        """Generate STAR-format behavioral answer."""
        # Match question to template
        q_lower = question.question.lower()

        if "lead" in q_lower or "manage" in q_lower:
            return self._format_star("leadership", profile)
        elif "conflict" in q_lower or "disagree" in q_lower:
            return self._format_star("conflict_resolution", profile)
        elif "fail" in q_lower or "mistake" in q_lower:
            return self._format_star("failure_learning", profile)
        elif "achiev" in q_lower or "proud" in q_lower or "accomplish" in q_lower:
            return self._format_star("project_success", profile)
        elif "challenge" in q_lower or "difficult" in q_lower:
            return self._format_star("problem_solving", profile)
        else:
            return self._format_star("problem_solving", profile)

    def _format_star(self, template_type: str, profile: Dict) -> str:
        """Format STAR response using profile data."""
        achievements = profile.get("achievements", [])
        experiences = profile.get("experiences", [])

        if not achievements:
            return self._generic_star(profile)

        achievement = achievements[0] if achievements else {}

        situation = achievement.get("situation", "In my previous role, we faced a significant challenge")
        task = achievement.get("task", "I was tasked with leading the solution")
        action = achievement.get("action", "I analyzed the problem, designed a solution, and led the implementation")
        result = achievement.get("result", "The project was delivered on time with 20% performance improvement")

        if template_type == "failure_learning":
            return f"Situation: {situation}\nTask: {task}\nAction: {action}\nResult: {result}\nLesson Learned: This experience taught me the importance of early stakeholder alignment."

        return f"Situation: {situation}\nTask: {task}\nAction: {action}\nResult: {result}"

    def _generic_star(self, profile: Dict) -> str:
        """Generate generic STAR response."""
        return """Situation: In my previous role as a senior engineer, our team faced a critical performance bottleneck in our main application.
Task: I was tasked with identifying and resolving the bottleneck before our major product launch.
Action: I conducted a thorough performance analysis using profiling tools, identified the root cause in our database query layer, redesigned the query patterns, implemented caching, and worked with the team to deploy the fixes.
Result: The application response time improved by 65%, we met our launch deadline, and the solution became our standard approach for performance optimization."""

    def _generate_situational_answer(self, question: ApplicationQuestion, profile: Dict) -> str:
        """Generate situational (what would you do) answer."""
        q_lower = question.question.lower()

        if "prioritize" in q_lower:
            return "I would prioritize by first assessing business impact and urgency, then using a framework like RICE (Reach, Impact, Confidence, Effort) to score each item. I'd communicate the rationale to stakeholders and adjust based on feedback."

        elif "deadline" in q_lower or "pressure" in q_lower:
            return "I would break the project into critical path items, identify what can be deferred, communicate realistic timelines to stakeholders, and focus the team on the highest-impact deliverables first."

        elif "conflict" in q_lower or "disagree" in q_lower:
            return "I would first seek to understand each perspective through active listening, find common ground, and propose a solution that addresses the core concerns. If needed, I'd escalate with a clear recommendation based on data."

        elif "mistake" in q_lower or "error" in q_lower:
            return "I would immediately acknowledge the mistake, assess the impact, communicate transparently with stakeholders, implement a fix, and document lessons learned to prevent recurrence."

        return "I would assess the situation, gather relevant information, consult with stakeholders, make a decision based on data and impact, and communicate clearly throughout the process."

    def _generate_technical_answer(self, question: ApplicationQuestion, profile: Dict) -> str:
        """Generate technical answer."""
        skills = profile.get("skills", [])
        q_lower = question.question.lower()

        # Extract key technologies from profile
        tech_stack = [s for s in skills if s.get("category") == "technical"]

        if "design" in q_lower or "architect" in q_lower:
            return f"I would approach this by first understanding the requirements and constraints. For a system requiring {question.keywords[0] if question.keywords else 'scalability'}, I'd choose {skills[0] if skills else 'appropriate technology'} for the core, implement {skills[1] if len(skills) > 1 else 'appropriate patterns'} for reliability, and ensure observability through monitoring and logging."

        elif "optimize" in q_lower or "performance" in q_lower:
            return "I would start by profiling to identify bottlenecks, then apply targeted optimizations: database indexing, query optimization, caching strategies, async processing, and horizontal scaling where appropriate. I'd measure at each step to validate improvements."

        elif "debug" in q_lower or "troubleshoot" in q_lower:
            return "My debugging process: 1) Reproduce the issue consistently, 2) Isolate the component, 3) Check logs and metrics, 4) Use binary search to narrow down the cause, 5) Implement fix with test coverage, 6) Verify in staging before production."

        return "I would approach this systematically: understand requirements, evaluate trade-offs, implement with best practices, test thoroughly, and document for maintainability."

    def _generate_experience_answer(self, question: ApplicationQuestion, profile: Dict) -> str:
        """Generate experience-based answer."""
        experiences = profile.get("experiences", [])
        skills = profile.get("skills", [])
        years = profile.get("years_experience", 0)

        q_lower = question.question.lower()

        if "describe your experience" in q_lower or "walk me through" in q_lower:
            if experiences:
                exp = experiences[0]
                # Build description with skills
                skill_names = ", ".join([s.get("name", "") for s in skills[:3]])
                desc_default = f"worked on various projects using {skill_names}"
                description = exp.get("description", desc_default)
                key_achievement = profile.get("achievements", ["delivered significant results"])[0]
                return f"I have {years} years of experience as a {exp.get('role', 'professional')}. At {exp.get('company', 'my company')}, I {description}. Key achievement: {key_achievement}."
            else:
                return f"I have {years} years of experience in {', '.join([s.get('name', '') for s in skills[:3]])}. My background includes {profile.get('summary', 'extensive experience in the field')}. Key strengths include problem-solving, collaboration, and delivering results."

        elif "specific" in q_lower and ("technology" in q_lower or "tool" in q_lower or "language" in q_lower):
            tech = question.keywords[0] if question.keywords else "the technology"
            relevant = [s for s in skills if tech.lower() in s.get("name", "").lower()]
            if relevant:
                return f"I have {relevant[0].get('proficiency', 'advanced')} proficiency in {tech} with {relevant[0].get('years', 'several')} years of hands-on experience. I've used it for {profile.get('achievements', ['building scalable applications'])[0]}."
            else:
                return f"While I haven't used {tech} extensively, I have strong fundamentals in similar technologies and can ramp up quickly. My experience with {', '.join([s.get('name', '') for s in skills[:3]])} gives me a solid foundation."

        return f"I bring {years} years of experience with a track record of delivering results in {', '.join([s.get('name', '') for s in skills[:3]])}."

    def _generate_motivation_answer(self, question: ApplicationQuestion, profile: Dict, target_company: Optional[str]) -> str:
        """Generate motivation/why us answer."""
        q_lower = question.question.lower()

        if "why this company" in q_lower or "why do you want" in q_lower:
            if target_company:
                return f"I've been following {target_company}'s work and admire your innovation in {self._infer_industry(target_company)}. Your recent work on {profile.get('company_project', 'innovative projects')} particularly resonates with me. Your values around innovation and impact align with my own professional philosophy, and I'm excited about the opportunity to contribute to {target_company}'s mission."
            return "I'm drawn to companies that solve meaningful problems with technology. I value innovation, collaboration, and continuous learning -- all of which I see reflected in your company's work."

        elif "why this role" in q_lower:
            return f"This role aligns perfectly with my {profile.get('years_experience', 0)}-year background in {profile.get('skills', [{}])[0].get('name', 'the field') if profile.get('skills') else 'the field'}. I'm particularly excited about the opportunity to {profile.get('career_goal', 'drive impact through technology')} while growing my expertise in {question.keywords[0] if question.keywords else 'the domain'}."

        elif "career goal" in q_lower or "where do you see yourself" in q_lower:
            return f"My goal is to progress into a {profile.get('target_role', 'senior leadership')} role where I can {profile.get('career_goal', 'drive technical strategy and mentor teams')}. This position offers the right balance of technical challenge and growth opportunity to help me achieve that."

        return f"I'm motivated by solving complex problems and delivering real impact. This role offers the technical challenges and growth environment I'm seeking."

    def _generate_salary_answer(self, question: ApplicationQuestion, profile: Dict) -> str:
        """Generate salary expectation answer."""
        years = profile.get("years_experience", 0)
        role = profile.get("target_role", "this role")
        location = profile.get("location", "the area")

        # Research-based range
        base = 80000 + (years * 8000)
        range_min = base
        range_max = base + 30000

        return f"Based on my {years} years of experience in {role} and current market rates for {location}, I'm targeting a base salary range of ${range_min:,}-${range_max:,}. I'm flexible and open to discussing total compensation including equity, bonus, and benefits."

    def _generate_availability_answer(self, question: ApplicationQuestion, profile: Dict) -> str:
        """Generate availability answer."""
        notice = profile.get("notice_period", "2 weeks")
        return f"I'm available to start after my notice period of {notice}. I can be flexible based on your timeline."

    def _generate_culture_fit_answer(self, question: ApplicationQuestion, profile: Dict) -> str:
        """Generate culture fit answer."""
        q_lower = question.question.lower()

        if "work style" in q_lower or "how do you work" in q_lower:
            return "I'm a collaborative problem-solver who values clear communication and iterative progress. I thrive in autonomous environments with clear goals, and I enjoy mentoring others while staying hands-on technically."

        elif "team" in q_lower:
            return "I believe the best teams combine diverse perspectives with shared accountability. I contribute by being reliable, communicative, and willing to help others succeed. I also value psychological safety and continuous feedback."

        elif "value" in q_lower or "mission" in q_lower:
            return "I'm driven by solving real problems for users and creating measurable impact. I value transparency, continuous learning, and building things that last. I look for environments where these values are shared."

        return "I value collaboration, continuous learning, and delivering quality work. I thrive in environments that encourage innovation and ownership."

    def _generate_generic_answer(self, question: ApplicationQuestion, profile: Dict) -> str:
        """Generate generic answer for unclassified questions."""
        return f"Based on my {profile.get('years_experience', 0)}-year background in {', '.join([s.get('name', '') for s in profile.get('skills', [])[:3]])}, I would approach this by leveraging my experience in {profile.get('key_strength', 'problem-solving')} to deliver a thoughtful solution."

    def _extract_key_points(self, answer: str, q_type: QuestionType) -> List[str]:
        """Extract key points from answer."""
        points = []

        if "situation:" in answer.lower() or "task:" in answer.lower():
            points.append("STAR format used")

        if re.search(r"\d+%|\$\d+|\d+\s*(?:years?|months?)", answer):
            points.append("Quantifiable metrics included")

        if "action" in answer.lower() and "result" in answer.lower():
            points.append("Action-result structure")

        if len(answer.split()) > 50:
            points.append("Comprehensive response")

        return points

    def _calculate_confidence(self, answer: str, question: ApplicationQuestion, profile: Dict) -> float:
        """Calculate confidence in answer quality."""
        score = 50

        # Length check
        words = len(answer.split())
        if 50 <= words <= 200:
            score += 20
        elif words > 200:
            score += 10
        elif words < 30:
            score -= 10

        # Structure check
        q_type = question.question_type
        if q_type == QuestionType.BEHAVIORAL and "situation:" in answer.lower():
            score += 15

        # Quantifiable metrics
        if re.search(r"\d+%|\$\d+", answer):
            score += 10

        # Specificity (mentions specific technologies, companies, metrics)
        specific_indicators = len(re.findall(r"\b[A-Z][a-z]+\b", answer))
        if specific_indicators > 3:
            score += 10

        return min(100, max(0, score))

    def _generate_answer_suggestions(
        self,
        answer: str,
        question: ApplicationQuestion,
        profile: Dict,
    ) -> List[str]:
        """Generate suggestions for improving the answer."""
        suggestions = []

        words = len(answer.split())
        if words < 50:
            suggestions.append("Expand your answer with more specific details and context")
        elif words > 300:
            suggestions.append("Consider condensing for conciseness -- aim for 100-200 words")

        if not re.search(r"\d+%|\$\d+|\d+\s*(?:years?|months?)", answer):
            suggestions.append("Add quantifiable metrics (percentages, dollar amounts, timeframes)")

        if "I think" in answer or "I believe" in answer:
            suggestions.append("Use more definitive language -- replace 'I think' with 'I achieved' or 'I delivered'")

        if not any(verb in answer.lower() for verb in ["led", "built", "created", "improved", "delivered", "achieved"]):
            suggestions.append("Include strong action verbs to demonstrate ownership")

        return suggestions[:3]

    def _generate_review_notes(self, answers: List[AnswerDraft], profile: Dict) -> List[str]:
        """Generate overall review notes."""
        notes = []

        avg_confidence = sum(a.confidence for a in answers) / len(answers) if answers else 0
        if avg_confidence < 70:
            notes.append("Overall answer quality could be improved -- consider adding more specific examples and metrics")

        behavioral_count = sum(1 for a in answers if a.question_type == QuestionType.BEHAVIORAL)
        if behavioral_count > 0:
            star_count = sum(1 for a in answers if a.question_type == QuestionType.BEHAVIORAL and "situation:" in a.answer.lower())
            if star_count < behavioral_count:
                notes.append("Some behavioral answers could use more structured STAR format")

        salary_answered = any(a.question_type == QuestionType.SALARY for a in answers)
        if not salary_answered:
            notes.append("Consider preparing a salary expectation answer with researched range")

        return notes

    def _infer_industry(self, company: str) -> str:
        """Infer industry from company name."""
        tech = ["google", "microsoft", "amazon", "meta", "apple", "netflix", "uber", "airbnb", "stripe"]
        if any(t in company.lower() for t in tech):
            return "technology"
        return "your industry"

    def generate_answer_for_question(
        self,
        question_text: str,
        candidate_profile: Dict[str, Any],
        target_role: Optional[str] = None,
        target_company: Optional[str] = None,
    ) -> str:
        """Generate answer for a single question string."""
        q = ApplicationQuestion(
            question=question_text,
            question_type=self._classify_question(question_text),
        )
        answer = self._generate_answer(q, candidate_profile, target_role, target_company)
        return answer.answer

    def optimize_answer(
        self,
        answer: str,
        question: str,
        target_role: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Optimize an existing answer."""
        suggestions = []

        # Check length
        words = len(answer.split())
        if words < 50:
            suggestions.append("Too brief -- expand with specific example")
        elif words > 250:
            suggestions.append("Consider condensing -- aim for 100-200 words")

        # Check for STAR
        if not any(kw in answer.lower() for kw in ["situation", "task", "action", "result"]):
            suggestions.append("Consider STAR format: Situation, Task, Action, Result")

        # Check for metrics
        if not re.search(r"\d+%|\$\d+|\d+\s*(?:years?|months?|people)", answer):
            suggestions.append("Add quantifiable metrics")

        # Check for weak language
        weak = [w for w in ["responsible for", "helped", "assisted", "worked on"] if w in answer.lower()]
        if weak:
            suggestions.append(f"Replace weak phrases: {', '.join(weak)}")

        # Check for action verbs
        if not any(v in answer.lower() for v in ["led", "built", "created", "improved", "delivered", "achieved", "optimized"]):
            suggestions.append("Add strong action verbs")

        return {
            "original": answer,
            "suggestions": suggestions,
            "word_count": len(answer.split()),
        }


from typing import Optional