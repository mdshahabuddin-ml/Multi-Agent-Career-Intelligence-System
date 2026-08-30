import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum as PyEnum

from backend.agents.career.skill_gap_agent import SkillGapAgent, SkillGapAnalysis, SkillGap
from backend.agents.career.career_path_agent import CareerPathAgent, CareerTrajectory, CareerPath
from backend.agents.career.learning_agent import LearningAgent, LearningPlan, LearningProgress, LearningStyle

logger = logging.getLogger(__name__)


class AdvisorFocus(str, PyEnum):
    SKILL_DEVELOPMENT = "skill_development"
    CAREER_TRANSITION = "career_transition"
    JOB_SEARCH = "job_search"
    SALARY_NEGOTIATION = "salary_negotiation"
    LEADERSHIP_GROWTH = "leadership_growth"
    WORK_LIFE_BALANCE = "work_life_balance"
    PERSONAL_BRANDING = "personal_branding"
    NETWORKING = "networking"


@dataclass
class CareerAdvice:
    """A piece of career advice."""
    focus: AdvisorFocus
    title: str
    description: str
    priority: int  # 1-5
    actionable_steps: List[str]
    resources: List[Dict[str, Any]]
    timeline: str
    confidence: float


@dataclass
class CareerAssessment:
    """Complete career assessment."""
    user_id: int
    current_role: str
    target_role: Optional[str]
    years_experience: int
    skills: List[Dict[str, Any]]
    skill_gap_analysis: Optional[SkillGapAnalysis]
    career_trajectory: Optional[CareerTrajectory]
    learning_plan: Optional[LearningPlan]
    advice: List[CareerAdvice]
    overall_score: float  # 0-100
    strengths: List[str]
    areas_for_improvement: List[str]
    next_actions: List[str]
    generated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class CareerGoal:
    """A career goal."""
    id: str
    user_id: int
    title: str
    description: str
    target_date: date
    target_role: Optional[str]
    target_skills: List[str]
    milestones: List[Dict[str, Any]]
    is_active: bool = True
    progress: float = 0.0


class CareerAdvisor:
    """Main career advisor that orchestrates all career intelligence agents."""

    def __init__(self):
        self.name = "career_advisor"
        self.skill_gap_agent = SkillGapAgent()
        self.career_path_agent = CareerPathAgent()
        self.learning_agent = LearningAgent()

    def assess_career(
        self,
        user_id: int,
        current_role: str,
        years_experience: int,
        skills: List[Dict[str, Any]],
        target_role: Optional[str] = None,
        interests: Optional[List[str]] = None,
        weekly_learning_hours: int = 10,
        learning_budget: float = 0.0,
        learning_style: LearningStyle = LearningStyle.MIXED,
    ) -> CareerAssessment:
        """Perform comprehensive career assessment."""
        logger.info(f"Assessing career for user {user_id}: {current_role}")

        # Normalize skills
        candidate_skills = self._normalize_skills(skills)

        # 1. Skill Gap Analysis
        skill_gap_analysis = None
        if target_role:
            skill_gap_analysis = self.skill_gap_agent.analyze_skill_gaps(
                candidate_skills=candidate_skills,
                target_role=target_role,
            )

        # 2. Career Trajectory
        career_trajectory = self.career_path_agent.generate_trajectory(
            current_role=current_role,
            current_skills=[s["name"] for s in skills],
            years_experience=years_experience,
            interests=interests,
        )

        # 3. Learning Plan
        learning_plan = None
        if skill_gap_analysis and skill_gap_analysis.gaps:
            learning_plan = self.learning_agent.generate_learning_plan(
                user_id=user_id,
                target_role=target_role or "Career Growth",
                target_skills=[g.skill_name for g in skill_gap_analysis.gaps if g.is_missing],
                current_skills=[s["name"] for s in skills],
                skill_gaps=[g.skill_name for g in skill_gap_analysis.gaps],
                weekly_hours=weekly_learning_hours,
                learning_style=learning_style,
                budget=learning_budget,
            )

        # 4. Generate Advice
        advice = self._generate_advice(
            current_role=current_role,
            target_role=target_role,
            years_experience=years_experience,
            skills=skills,
            skill_gap_analysis=skill_gap_analysis,
            career_trajectory=career_trajectory,
            learning_plan=learning_plan,
        )

        # Calculate overall score
        overall_score = self._calculate_overall_score(
            skill_gap_analysis, career_trajectory, years_experience
        )

        # Identify strengths and areas for improvement
        strengths, improvements = self._identify_strengths_weaknesses(
            skills, skill_gap_analysis, years_experience
        )

        # Generate next actions
        next_actions = self._generate_next_actions(
            skill_gap_analysis, career_trajectory, learning_plan, advice
        )

        return CareerAssessment(
            user_id=user_id,
            current_role=current_role,
            target_role=target_role,
            years_experience=years_experience,
            skills=skills,
            skill_gap_analysis=skill_gap_analysis,
            career_trajectory=career_trajectory,
            learning_plan=learning_plan,
            advice=advice,
            overall_score=overall_score,
            strengths=strengths,
            areas_for_improvement=improvements,
            next_actions=next_actions,
        )

    def create_career_goal(
        self,
        user_id: int,
        title: str,
        description: str,
        target_date: date,
        target_role: Optional[str] = None,
        target_skills: Optional[List[str]] = None,
    ) -> CareerGoal:
        """Create a new career goal."""
        return CareerGoal(
            id=f"goal_{user_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            user_id=user_id,
            title=title,
            description=description,
            target_date=target_date,
            target_role=target_role,
            target_skills=target_skills or [],
            milestones=[],
            is_active=True,
        )

    def update_goal_progress(
        self,
        goal: CareerGoal,
        completed_milestones: List[str],
    ) -> CareerGoal:
        """Update goal progress."""
        # Update progress based on completed milestones
        if goal.milestones:
            completed = sum(1 for m in goal.milestones if m.get("title") in completed_milestones)
            goal.progress = completed / len(goal.milestones)
        return goal

    def get_personalized_job_search_strategy(
        self,
        assessment: CareerAssessment,
    ) -> Dict[str, Any]:
        """Generate personalized job search strategy based on assessment."""
        strategy = {
            "target_roles": [],
            "key_skills_to_highlight": [],
            "skill_gaps_to_address": [],
            "networking_strategy": [],
            "application_timeline": "immediate",
            "salary_expectations": {},
            "preparation_checklist": [],
        }

        if assessment.target_role:
            strategy["target_roles"].append(assessment.target_role)

        if assessment.career_trajectory and assessment.career_trajectory.recommended_path:
            path = assessment.career_trajectory.recommended_path
            for t in path.transitions:
                strategy["target_roles"].append(t.to_role)

        if assessment.skill_gap_analysis:
            strategy["skill_gaps_to_address"] = [
                g.skill_name for g in assessment.skill_gap_analysis.gaps
                if g.gap_severity > 0.5
            ]

        if assessment.skill_gap_analysis:
            strategy["key_skills_to_highlight"] = [
                m["skill"] for m in assessment.skill_gap_analysis.matched_skills
                if m.get("match_quality", 0) > 0.7
            ]

        # Networking strategy
        strategy["networking_strategy"] = [
            "Connect with 3 professionals in target role per week",
            "Join 2 relevant industry communities/groups",
            "Share 1 technical insight per week on LinkedIn",
            "Attend 1 virtual/in-person event per month",
        ]

        # Preparation checklist
        strategy["preparation_checklist"] = [
            "Update resume with quantified achievements",
            "Optimize LinkedIn profile for target role keywords",
            "Prepare STAR stories for behavioral interviews",
            "Practice technical interviews (if applicable)",
            "Research target companies and their interview processes",
            "Prepare questions for interviewers",
        ]

        return strategy

    def _normalize_skills(self, skills: List[Dict[str, Any]]) -> List:
        """Normalize skills to CandidateSkill objects."""
        from backend.agents.career.skill_gap_agent import CandidateSkill, SkillCategory, ProficiencyLevel

        normalized = []
        for skill in skills:
            normalized.append(CandidateSkill(
                name=skill.get("name", ""),
                category=SkillCategory(skill.get("category", "technical")),
                proficiency=ProficiencyLevel(skill.get("proficiency", "intermediate")),
                years_experience=skill.get("years_experience", 0),
                confidence=skill.get("confidence", 1.0),
            ))
        return normalized

    def _generate_advice(
        self,
        current_role: str,
        target_role: Optional[str],
        years_experience: int,
        skills: List[Dict[str, Any]],
        skill_gap_analysis: Optional[SkillGapAnalysis],
        career_trajectory: Optional[CareerTrajectory],
        learning_plan: Optional[LearningPlan],
    ) -> List[CareerAdvice]:
        """Generate personalized career advice."""
        advice = []

        # Skill development advice
        if skill_gap_analysis and skill_gap_analysis.critical_gaps_count > 0:
            top_gaps = [g for g in skill_gap_analysis.gaps if g.gap_severity > 0.7][:3]
            advice.append(CareerAdvice(
                focus=AdvisorFocus.SKILL_DEVELOPMENT,
                title=f"Close Critical Skill Gaps for {target_role or 'Career Growth'}",
                description=f"You have {len(top_gaps)} critical skill gaps that are essential for your target role.",
                priority=5,
                actionable_steps=[
                    f"Start learning {g.skill_name} this week" for g in top_gaps
                ] + [
                    f"Build a portfolio project demonstrating {g.skill_name}" for g in top_gaps
                ],
                resources=[{"type": "learning", "skills": [g.skill_name for g in top_gaps]}],
                timeline="2-4 weeks per skill",
                confidence=0.9,
            ))

        # Career transition advice
        if career_trajectory and career_trajectory.recommended_path:
            path = career_trajectory.recommended_path
            if path.transitions:
                first_transition = path.transitions[0]
                advice.append(CareerAdvice(
                    focus=AdvisorFocus.CAREER_TRANSITION,
                    title=f"Plan Transition to {first_transition.to_role}",
                    description=f"Recommended next step: {first_transition.transition_type.value} move to {first_transition.to_role} in ~{first_transition.estimated_time_months} months.",
                    priority=4,
                    actionable_steps=[
                        f"Learn required skills: {', '.join(first_transition.required_additional_skills[:3])}",
                        "Network with professionals in target role",
                        "Update resume for target role",
                        "Apply to 5+ positions per week",
                    ],
                    resources=[{"type": "career", "transition": first_transition.to_role}],
                    timeline=f"{first_transition.estimated_time_months} months",
                    confidence=0.8,
                ))

        # Learning plan advice
        if learning_plan:
            advice.append(CareerAdvice(
                focus=AdvisorFocus.SKILL_DEVELOPMENT,
                title=f"Follow {learning_plan.total_estimated_weeks}-Week Learning Plan",
                description=f"Structured plan to close skill gaps with {learning_plan.weekly_time_commitment_hours} hours/week.",
                priority=4,
                actionable_steps=[
                    f"Start Phase 1: {learning_plan.phases[0].name if learning_plan.phases else 'Foundation'}",
                    f"Commit {learning_plan.weekly_time_commitment_hours} hours/week consistently",
                    "Track progress weekly",
                    "Adjust plan monthly based on progress",
                ],
                resources=[{"type": "learning_plan", "plan_id": learning_plan.id}],
                timeline=f"{learning_plan.total_estimated_weeks} weeks",
                confidence=0.85,
            ))

        # Job search advice
        if target_role:
            advice.append(CareerAdvice(
                focus=AdvisorFocus.JOB_SEARCH,
                title=f"Optimize Job Search for {target_role}",
                description="Strategic approach to landing your target role.",
                priority=4,
                actionable_steps=[
                    "Tailor resume for each application with target role keywords",
                    "Build 2-3 portfolio projects showcasing target skills",
                    "Set up job alerts on LinkedIn, Indeed, company career pages",
                    "Practice interview questions specific to target role",
                    "Get referrals through network connections",
                ],
                resources=[{"type": "job_search", "role": target_role}],
                timeline="Ongoing, 10-15 applications/week",
                confidence=0.8,
            ))

        # Salary negotiation
        if career_trajectory and career_trajectory.recommended_path:
            path = career_trajectory.recommended_path
            if path.total_salary_growth_pct > 10:
                advice.append(CareerAdvice(
                    focus=AdvisorFocus.SALARY_NEGOTIATION,
                    title=f"Prepare for Salary Negotiation (+{path.total_salary_growth_pct:.0f}% potential)",
                    description=f"Your target role offers significant salary growth potential.",
                    priority=3,
                    actionable_steps=[
                        "Research market rates for target role and location",
                        "Document your quantified achievements",
                        "Practice negotiation scenarios",
                        "Determine your walk-away number",
                        "Prepare to discuss total compensation (equity, bonus, benefits)",
                    ],
                    resources=[{"type": "salary", "data": "market_research"}],
                    timeline="Before receiving offers",
                    confidence=0.75,
                ))

        # Leadership growth
        if years_experience >= 5:
            advice.append(CareerAdvice(
                focus=AdvisorFocus.LEADERSHIP_GROWTH,
                title="Develop Leadership Skills",
                description="With 5+ years experience, start building leadership capabilities for senior roles.",
                priority=3,
                actionable_steps=[
                    "Mentor a junior team member",
                    "Lead a small project or initiative",
                    "Take a leadership/management course",
                    "Practice giving constructive feedback",
                    "Volunteer for cross-functional projects",
                ],
                resources=[{"type": "course", "topic": "Leadership"}],
                timeline="6-12 months",
                confidence=0.8,
            ))

        # Personal branding
        advice.append(CareerAdvice(
            focus=AdvisorFocus.PERSONAL_BRANDING,
            title="Build Your Professional Brand",
            description="Establish yourself as an expert in your domain.",
            priority=3,
            actionable_steps=[
                "Optimize LinkedIn profile with target role keywords",
                "Write 1 technical blog post per month",
                "Speak at 1 meetup/conference per quarter",
                "Contribute to open source or community projects",
                "Build a portfolio website",
            ],
            resources=[{"type": "branding", "platforms": ["LinkedIn", "GitHub", "Personal Site"]}],
            timeline="Ongoing, 2-3 hours/week",
            confidence=0.85,
        ))

        # Networking
        advice.append(CareerAdvice(
            focus=AdvisorFocus.NETWORKING,
            title="Expand Professional Network Strategically",
            description="Your network is your net worth in career advancement.",
            priority=3,
            actionable_steps=[
                "Connect with 3 professionals in target role per week",
                "Join 2 industry-specific communities",
                "Engage meaningfully with content from target companies",
                "Offer help before asking for favors",
                "Schedule 1 coffee chat per week",
            ],
            resources=[{"type": "networking", "platforms": ["LinkedIn", "Twitter", "Discord", "Meetup"]}],
            timeline="Ongoing",
            confidence=0.9,
        ))

        # Work-life balance
        advice.append(CareerAdvice(
            focus=AdvisorFocus.WORK_LIFE_BALANCE,
            title="Maintain Sustainable Career Growth",
            description="Long-term success requires sustainable practices.",
            priority=2,
            actionable_steps=[
                "Set boundaries: no work emails after hours",
                "Schedule learning time like meetings",
                "Take regular breaks (Pomodoro technique)",
                "Exercise 3x/week minimum",
                "Quarterly career reflection and adjustment",
            ],
            resources=[{"type": "wellness", "topics": ["Boundaries", "Productivity", "Health"]}],
            timeline="Ongoing",
            confidence=0.95,
        ))

        return advice

    def _calculate_overall_score(
        self,
        skill_gap_analysis: Optional[SkillGapAnalysis],
        career_trajectory: Optional[CareerTrajectory],
        years_experience: int,
    ) -> float:
        """Calculate overall career readiness score (0-100)."""
        score = 50.0  # Base score

        # Experience factor (max 20 points)
        exp_score = min(years_experience * 2, 20)
        score += exp_score

        # Skill gap factor (max 20 points)
        if skill_gap_analysis:
            score += skill_gap_analysis.overall_match_score * 20
        else:
            score += 10  # Neutral if no analysis

        # Trajectory clarity (max 10 points)
        if career_trajectory and career_trajectory.recommended_path:
            score += 10

        return min(100, round(score, 1))

    def _identify_strengths_weaknesses(
        self,
        skills: List[Dict[str, Any]],
        skill_gap_analysis: Optional[SkillGapAnalysis],
        years_experience: int,
    ) -> tuple:
        """Identify strengths and areas for improvement."""
        strengths = []
        improvements = []

        # Experience as strength
        if years_experience >= 5:
            strengths.append(f"{years_experience} years of professional experience")
        elif years_experience >= 2:
            strengths.append(f"{years_experience} years of solid experience")

        # High proficiency skills
        for skill in skills:
            if skill.get("proficiency") in ["advanced", "expert"]:
                strengths.append(f"Strong {skill.get('category', 'technical')} skill: {skill.get('name')}")

        # Matched skills from gap analysis
        if skill_gap_analysis:
            for match in skill_gap_analysis.matched_skills:
                if match.get("match_quality", 0) > 0.8:
                    strengths.append(f"Well-matched: {match['skill']} ({match.get('candidate_proficiency', 'N/A')})")

        # Skill gaps as improvements
        if skill_gap_analysis:
            for gap in skill_gap_analysis.gaps:
                if gap.is_missing:
                    improvements.append(f"Missing critical skill: {gap.skill_name}")
                elif gap.gap_severity > 0.5:
                    improvements.append(f"Proficiency gap in {gap.skill_name}: {gap.candidate_proficiency.value if gap.candidate_proficiency else 'N/A'} -> {gap.required_proficiency.value}")

        # Low proficiency skills
        for skill in skills:
            if skill.get("proficiency") == "beginner":
                improvements.append(f"Develop {skill.get('name')} from beginner level")

        return strengths[:5], improvements[:5]

    def _generate_next_actions(
        self,
        skill_gap_analysis: Optional[SkillGapAnalysis],
        career_trajectory: Optional[CareerTrajectory],
        learning_plan: Optional[LearningPlan],
        advice: List[CareerAdvice],
    ) -> List[str]:
        """Generate prioritized next actions."""
        actions = []

        # High priority: Critical skill gaps
        if skill_gap_analysis and skill_gap_analysis.critical_gaps_count > 0:
            top_gap = skill_gap_analysis.gaps[0]
            actions.append(f"Start learning {top_gap.skill_name} this week (critical gap)")

        # High priority: First career transition
        if career_trajectory and career_trajectory.recommended_path:
            first = career_trajectory.recommended_path.transitions[0] if career_trajectory.recommended_path.transitions else None
            if first:
                actions.append(f"Begin transition to {first.to_role}: learn {', '.join(first.required_additional_skills[:2])}")

        # Medium priority: Learning plan
        if learning_plan and learning_plan.phases:
            actions.append(f"Enroll in Phase 1: {learning_plan.phases[0].name}")

        # Medium priority: Job search prep
        actions.append("Update resume with quantified achievements for target role")

        # Medium priority: Networking
        actions.append("Connect with 3 professionals in target role this week")

        # Low priority: Brand building
        actions.append("Write and publish one technical article this month")

        return actions[:5]