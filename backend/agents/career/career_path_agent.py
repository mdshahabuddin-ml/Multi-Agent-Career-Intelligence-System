import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum as PyEnum

logger = logging.getLogger(__name__)


class CareerStage(str, PyEnum):
    ENTRY = "entry"
    JUNIOR = "junior"
    MID = "mid"
    SENIOR = "senior"
    LEAD = "lead"
    PRINCIPAL = "principal"
    DIRECTOR = "director"
    VP = "vp"
    C_LEVEL = "c_level"


class TransitionType(str, PyEnum):
    VERTICAL = "vertical"  # Promotion within same track
    LATERAL = "lateral"  # Same level, different role
    PIVOT = "pivot"  # Significant career change
    ENTREPRENEURSHIP = "entrepreneurship"  # Starting own venture


@dataclass
class CareerPathNode:
    """A node in the career path graph."""
    role: str
    stage: CareerStage
    typical_years_experience: int
    required_skills: List[str]
    average_salary_range: tuple  # (min, max)
    common_next_roles: List[str]
    description: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "stage": self.stage.value,
            "typical_years_experience": self.typical_years_experience,
            "required_skills": self.required_skills,
            "average_salary_range": self.average_salary_range,
            "common_next_roles": self.common_next_roles,
            "description": self.description,
        }


@dataclass
class CareerTransition:
    """A possible career transition."""
    from_role: str
    to_role: str
    transition_type: TransitionType
    difficulty: float  # 0-1
    required_additional_skills: List[str]
    estimated_time_months: int
    salary_change_pct: float  # Expected salary change %
    success_factors: List[str]
    risks: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "from_role": self.from_role,
            "to_role": self.to_role,
            "transition_type": self.transition_type.value,
            "difficulty": self.difficulty,
            "required_additional_skills": self.required_additional_skills,
            "estimated_time_months": self.estimated_time_months,
            "salary_change_pct": self.salary_change_pct,
            "success_factors": self.success_factors,
            "risks": self.risks,
        }


@dataclass
class CareerPath:
    """A complete career path."""
    current_role: str
    target_role: str
    current_stage: CareerStage
    target_stage: CareerStage
    path_nodes: List[CareerPathNode]
    transitions: List[CareerTransition]
    total_estimated_time_months: int
    total_salary_growth_pct: float
    milestones: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "current_role": self.current_role,
            "target_role": self.target_role,
            "current_stage": self.current_stage.value,
            "target_stage": self.target_stage.value,
            "path_nodes": [n.to_dict() for n in self.path_nodes],
            "transitions": [t.to_dict() for t in self.transitions],
            "total_estimated_time_months": self.total_estimated_time_months,
            "total_salary_growth_pct": self.total_salary_growth_pct,
            "milestones": self.milestones,
        }


@dataclass
class CareerTrajectory:
    """Multiple possible career trajectories."""
    current_role: str
    current_stage: CareerStage
    years_experience: int
    current_skills: List[str]
    possible_paths: List[CareerPath]
    recommended_path: CareerPath
    alternative_paths: List[CareerPath]
    decision_factors: Dict[str, float]  # Factors to consider

    def to_dict(self) -> Dict[str, Any]:
        return {
            "current_role": self.current_role,
            "current_stage": self.current_stage.value,
            "years_experience": self.years_experience,
            "current_skills": self.current_skills,
            "possible_paths": [p.to_dict() for p in self.possible_paths],
            "recommended_path": self.recommended_path.to_dict() if self.recommended_path else None,
            "alternative_paths": [p.to_dict() for p in self.alternative_paths],
            "decision_factors": self.decision_factors,
        }


class CareerPathAgent:
    """Generate career paths and transitions."""

    def __init__(self):
        self.name = "career_path_agent"
        self._career_graph = self._initialize_career_graph()

    def _initialize_career_graph(self) -> Dict[str, CareerPathNode]:
        """Initialize the career progression graph."""
        return {
            # Software Engineering Track
            "junior software engineer": CareerPathNode(
                role="Junior Software Engineer",
                stage=CareerStage.JUNIOR,
                typical_years_experience=1,
                required_skills=["Programming", "Git", "Basic Algorithms", "Debugging"],
                average_salary_range=(70000, 100000),
                common_next_roles=["Software Engineer", "Full Stack Developer", "Backend Developer"],
                description="Entry-level developer learning fundamentals",
            ),
            "software engineer": CareerPathNode(
                role="Software Engineer",
                stage=CareerStage.MID,
                typical_years_experience=3,
                required_skills=["System Design", "Testing", "CI/CD", "Databases", "APIs"],
                average_salary_range=(100000, 140000),
                common_next_roles=["Senior Software Engineer", "Tech Lead", "Staff Engineer"],
                description="Independent contributor building features end-to-end",
            ),
            "senior software engineer": CareerPathNode(
                role="Senior Software Engineer",
                stage=CareerStage.SENIOR,
                typical_years_experience=5,
                required_skills=["Architecture", "Mentoring", "Code Review", "Performance Optimization"],
                average_salary_range=(140000, 180000),
                common_next_roles=["Staff Engineer", "Engineering Manager", "Principal Engineer"],
                description="Leads complex projects, mentors juniors, drives technical decisions",
            ),
            "staff engineer": CareerPathNode(
                role="Staff Engineer",
                stage=CareerStage.LEAD,
                typical_years_experience=8,
                required_skills=["Technical Strategy", "Cross-team Leadership", "Architecture"],
                average_salary_range=(180000, 250000),
                common_next_roles=["Principal Engineer", "Director of Engineering"],
                description="Technical leader across multiple teams, sets technical direction",
            ),
            "principal engineer": CareerPathNode(
                role="Principal Engineer",
                stage=CareerStage.PRINCIPAL,
                typical_years_experience=12,
                required_skills=["Organization-wide Strategy", "Technical Vision", "Executive Communication"],
                average_salary_range=(250000, 350000),
                common_next_roles=["VP Engineering", "CTO", "Technical Fellow"],
                description="Top technical leader, influences company-wide technical strategy",
            ),
            "engineering manager": CareerPathNode(
                role="Engineering Manager",
                stage=CareerStage.LEAD,
                typical_years_experience=6,
                required_skills=["People Management", "Project Management", "Hiring", "Budgeting"],
                average_salary_range=(150000, 220000),
                common_next_roles=["Director of Engineering", "VP Engineering"],
                description="Manages engineering teams, responsible for delivery and people",
            ),
            "director of engineering": CareerPathNode(
                role="Director of Engineering",
                stage=CareerStage.DIRECTOR,
                typical_years_experience=10,
                required_skills=["Organizational Leadership", "Strategy", "Budget Management"],
                average_salary_range=(220000, 350000),
                common_next_roles=["VP Engineering", "CTO"],
                description="Leads multiple engineering managers, owns engineering strategy",
            ),

            # Data Science Track
            "junior data scientist": CareerPathNode(
                role="Junior Data Scientist",
                stage=CareerStage.JUNIOR,
                typical_years_experience=1,
                required_skills=["Python", "Statistics", "ML Basics", "Data Viz"],
                average_salary_range=(80000, 110000),
                common_next_roles=["Data Scientist", "ML Engineer", "Analytics Engineer"],
                description="Entry-level data scientist building models and analyzing data",
            ),
            "data scientist": CareerPathNode(
                role="Data Scientist",
                stage=CareerStage.MID,
                typical_years_experience=3,
                required_skills=["Advanced ML", "Experiment Design", "Production ML", "Domain Expertise"],
                average_salary_range=(110000, 150000),
                common_next_roles=["Senior Data Scientist", "Lead Data Scientist", "ML Engineer"],
                description="Builds and deploys ML models, drives data-driven decisions",
            ),
            "senior data scientist": CareerPathNode(
                role="Senior Data Scientist",
                stage=CareerStage.SENIOR,
                typical_years_experience=5,
                required_skills=["Advanced ML", "Research", "Mentoring", "Business Strategy"],
                average_salary_range=(150000, 200000),
                common_next_roles=["Lead Data Scientist", "Principal Data Scientist", "ML Manager"],
                description="Leads ML initiatives, mentors team, drives ML strategy",
            ),

            # Product Management Track
            "associate product manager": CareerPathNode(
                role="Associate Product Manager",
                stage=CareerStage.ENTRY,
                typical_years_experience=1,
                required_skills=["User Research", "Analytics", "Roadmapping", "Communication"],
                average_salary_range=(80000, 110000),
                common_next_roles=["Product Manager", "Technical Product Manager"],
                description="Entry-level PM learning product development lifecycle",
            ),
            "product manager": CareerPathNode(
                role="Product Manager",
                stage=CareerStage.MID,
                typical_years_experience=3,
                required_skills=["Strategy", "Prioritization", "Stakeholder Management", "Metrics"],
                average_salary_range=(120000, 170000),
                common_next_roles=["Senior Product Manager", "Group Product Manager"],
                description="Owns product area, defines roadmap, works with engineering/design",
            ),
            "senior product manager": CareerPathNode(
                role="Senior Product Manager",
                stage=CareerStage.SENIOR,
                typical_years_experience=5,
                required_skills=["Product Strategy", "Org Influence", "Complex Problem Solving"],
                average_salary_range=(170000, 230000),
                common_next_roles=["Group Product Manager", "Director of Product", "VP Product"],
                description="Leads complex products, influences cross-functional strategy",
            ),

            # DevOps/Platform Track
            "devops engineer": CareerPathNode(
                role="DevOps Engineer",
                stage=CareerStage.MID,
                typical_years_experience=3,
                required_skills=["AWS/GCP/Azure", "Kubernetes", "Terraform", "CI/CD", "Monitoring"],
                average_salary_range=(110000, 150000),
                common_next_roles=["Senior DevOps Engineer", "Platform Engineer", "SRE"],
                description="Builds and maintains infrastructure, automates deployments",
            ),
            "site reliability engineer": CareerPathNode(
                role="Site Reliability Engineer",
                stage=CareerStage.SENIOR,
                typical_years_experience=5,
                required_skills=["Incident Response", "Capacity Planning", "Chaos Engineering", "Observability"],
                average_salary_range=(140000, 200000),
                common_next_roles=["Senior SRE", "SRE Manager", "Platform Lead"],
                description="Ensures system reliability, builds automation, manages incidents",
            ),
        }

    def generate_career_path(
        self,
        current_role: str,
        target_role: str,
        current_skills: List[str],
        years_experience: int,
    ) -> CareerPath:
        """Generate a career path from current to target role."""
        logger.info(f"Generating career path: {current_role} -> {target_role}")

        current_node = self._career_graph.get(current_role.lower())
        target_node = self._career_graph.get(target_role.lower())

        if not current_node or not target_node:
            return self._generate_generic_path(current_role, target_role, current_skills, years_experience)

        # Find path through graph (simplified - would use BFS/DFS in production)
        path_nodes = self._find_path(current_node, target_node)
        transitions = self._generate_transitions(path_nodes)
        milestones = self._generate_milestones(path_nodes, current_skills)

        total_time = sum(t.estimated_time_months for t in transitions)
        salary_growth = self._calculate_salary_growth(path_nodes)

        return CareerPath(
            current_role=current_role,
            target_role=target_role,
            current_stage=current_node.stage,
            target_stage=target_node.stage,
            path_nodes=path_nodes,
            transitions=transitions,
            total_estimated_time_months=total_time,
            total_salary_growth_pct=salary_growth,
            milestones=milestones,
        )

    def generate_trajectory(
        self,
        current_role: str,
        current_skills: List[str],
        years_experience: int,
        interests: Optional[List[str]] = None,
    ) -> CareerTrajectory:
        """Generate multiple possible career trajectories."""
        logger.info(f"Generating career trajectories for: {current_role}")

        current_node = self._career_graph.get(current_role.lower())
        if not current_node:
            current_stage = self._infer_stage(years_experience)
        else:
            current_stage = current_node.stage

        # Generate possible next roles based on graph
        possible_paths = []
        if current_node:
            for next_role in current_node.common_next_roles:
                path = self.generate_career_path(current_role, next_role, current_skills, years_experience)
                possible_paths.append(path)

        # If no next roles, suggest based on interests
        if not possible_paths and interests:
            for interest in interests:
                matching_roles = self._find_roles_by_interest(interest)
                for role in matching_roles[:3]:
                    path = self.generate_career_path(current_role, role, current_skills, years_experience)
                    possible_paths.append(path)

        # Score and rank paths
        scored_paths = self._score_paths(possible_paths, current_skills, interests or [])

        recommended = scored_paths[0] if scored_paths else None
        alternatives = scored_paths[1:] if len(scored_paths) > 1 else []

        return CareerTrajectory(
            current_role=current_role,
            current_stage=current_stage,
            years_experience=years_experience,
            current_skills=current_skills,
            possible_paths=possible_paths,
            recommended_path=recommended,
            alternative_paths=alternatives,
            decision_factors={
                "salary_growth": 0.25,
                "skill_alignment": 0.30,
                "market_demand": 0.20,
                "learning_curve": 0.15,
                "work_life_balance": 0.10,
            },
        )

    def _find_path(self, start: CareerPathNode, target: CareerPathNode) -> List[CareerPathNode]:
        """Find path between two nodes (simplified BFS)."""
        if start.role == target.role:
            return [start]

        # Simple path: current -> intermediate -> target
        # In production, would use proper graph search
        path = [start]

        # Check if target is directly reachable
        if target.role in start.common_next_roles:
            path.append(target)
            return path

        # Try one intermediate step
        for next_role in start.common_next_roles:
            next_node = self._career_graph.get(next_role.lower())
            if next_node and target.role in next_node.common_next_roles:
                return [start, next_node, target]

        # Fallback: direct path
        return [start, target]

    def _generate_transitions(self, path_nodes: List[CareerPathNode]) -> List[CareerTransition]:
        """Generate transitions between path nodes."""
        transitions = []
        for i in range(len(path_nodes) - 1):
            from_node = path_nodes[i]
            to_node = path_nodes[i + 1]

            # Calculate required skills
            required_skills = [s for s in to_node.required_skills if s not in from_node.required_skills]

            # Estimate time
            exp_diff = to_node.typical_years_experience - from_node.typical_years_experience
            time_months = max(12, exp_diff * 12)  # At least 1 year

            # Salary change
            from_salary = sum(from_node.average_salary_range) / 2
            to_salary = sum(to_node.average_salary_range) / 2
            salary_change = ((to_salary - from_salary) / from_salary * 100) if from_salary > 0 else 0

            # Determine transition type
            if to_node.stage.value > from_node.stage.value:
                trans_type = TransitionType.VERTICAL
            elif to_node.stage.value == from_node.stage.value:
                trans_type = TransitionType.LATERAL
            else:
                trans_type = TransitionType.PIVOT

            transitions.append(CareerTransition(
                from_role=from_node.role,
                to_role=to_node.role,
                transition_type=trans_type,
                difficulty=0.5 + (exp_diff * 0.05),
                required_additional_skills=required_skills,
                estimated_time_months=time_months,
                salary_change_pct=round(salary_change, 1),
                success_factors=[
                    f"Master {s}" for s in required_skills[:3]
                ] + ["Build relevant projects", "Network with professionals in role"],
                risks=[
                    "Skill gap may take longer to close",
                    "Market conditions may change",
                    "Internal opportunities may be limited",
                ],
            ))

        return transitions

    def _generate_milestones(
        self,
        path_nodes: List[CareerPathNode],
        current_skills: List[str],
    ) -> List[Dict[str, Any]]:
        """Generate milestones along the path."""
        milestones = []
        cumulative_months = 0

        for i, node in enumerate(path_nodes[1:], 1):
            missing_skills = [s for s in node.required_skills if s not in current_skills]
            cumulative_months += 12  # Approximate

            milestones.append({
                "milestone": f"Reach {node.role}",
                "target_month": cumulative_months,
                "required_skills": missing_skills[:5],
                "skills_to_learn": missing_skills,
                "salary_range": node.average_salary_range,
                "key_projects": self._suggest_projects(node.role, missing_skills[:3]),
            })

        return milestones

    def _suggest_projects(self, role: str, skills: List[str]) -> List[str]:
        """Suggest portfolio projects for role."""
        project_map = {
            "Software Engineer": ["Full-stack web app", "REST API with database", "Microservice demo"],
            "Data Scientist": ["End-to-end ML project", "Kaggle competition", "Data viz dashboard"],
            "DevOps Engineer": ["Kubernetes cluster setup", "CI/CD pipeline", "Infrastructure as code"],
            "Product Manager": ["Product strategy doc", "User research report", "Roadmap presentation"],
        }
        return project_map.get(role, ["Build portfolio project", "Open source contribution", "Technical blog post"])

    def _calculate_salary_growth(self, path_nodes: List[CareerPathNode]) -> float:
        """Calculate total salary growth percentage."""
        if len(path_nodes) < 2:
            return 0.0
        start = sum(path_nodes[0].average_salary_range) / 2
        end = sum(path_nodes[-1].average_salary_range) / 2
        return round(((end - start) / start * 100) if start > 0 else 0, 1)

    def _generate_generic_path(
        self,
        current_role: str,
        target_role: str,
        current_skills: List[str],
        years_experience: int,
    ) -> CareerPath:
        """Generate generic path when roles not in graph."""
        return CareerPath(
            current_role=current_role,
            target_role=target_role,
            current_stage=self._infer_stage(years_experience),
            target_stage=self._infer_stage(years_experience + 3),
            path_nodes=[],
            transitions=[CareerTransition(
                from_role=current_role,
                to_role=target_role,
                transition_type=TransitionType.PIVOT,
                difficulty=0.7,
                required_additional_skills=["Role-specific skills"],
                estimated_time_months=18,
                salary_change_pct=10.0,
                success_factors=["Research role requirements", "Build relevant projects"],
                risks=["Significant career change", "May need additional education"],
            )],
            total_estimated_time_months=18,
            total_salary_growth_pct=10.0,
            milestones=[{
                "milestone": f"Transition to {target_role}",
                "target_month": 18,
                "skills_to_learn": ["Role-specific skills"],
            }],
        )

    def _infer_stage(self, years_experience: int) -> CareerStage:
        """Infer career stage from years of experience."""
        if years_experience <= 1:
            return CareerStage.ENTRY
        elif years_experience <= 3:
            return CareerStage.JUNIOR
        elif years_experience <= 5:
            return CareerStage.MID
        elif years_experience <= 8:
            return CareerStage.SENIOR
        elif years_experience <= 12:
            return CareerStage.LEAD
        elif years_experience <= 15:
            return CareerStage.PRINCIPAL
        elif years_experience <= 20:
            return CareerStage.DIRECTOR
        else:
            return CareerStage.VP

    def _find_roles_by_interest(self, interest: str) -> List[str]:
        """Find roles matching interest."""
        interest_map = {
            "ai": ["Machine Learning Engineer", "Data Scientist", "AI Researcher"],
            "backend": ["Software Engineer", "Backend Developer", "API Engineer"],
            "frontend": ["Frontend Developer", "Full Stack Developer", "UI Engineer"],
            "devops": ["DevOps Engineer", "Platform Engineer", "SRE"],
            "management": ["Engineering Manager", "Tech Lead", "Product Manager"],
            "data": ["Data Scientist", "Data Engineer", "Analytics Engineer"],
            "security": ["Security Engineer", "DevSecOps Engineer", "Application Security Engineer"],
            "mobile": ["Mobile Developer", "iOS Developer", "Android Developer"],
        }
        return interest_map.get(interest.lower(), ["Software Engineer"])

    def _score_paths(
        self,
        paths: List[CareerPath],
        current_skills: List[str],
        interests: List[str],
    ) -> List[CareerPath]:
        """Score and rank career paths."""
        for path in paths:
            score = 0.0

            # Skill alignment
            if path.transitions:
                all_required = set()
                for t in path.transitions:
                    all_required.update(t.required_additional_skills)
                current_skills_set = set(current_skills)
                skill_match = len(current_skills_set & all_required) / len(all_required) if all_required else 1
                score += skill_match * 0.3

            # Salary growth
            score += min(path.total_salary_growth_pct / 100, 1.0) * 0.2

            # Time efficiency (shorter is better)
            time_score = max(0, 1 - path.total_estimated_time_months / 60)
            score += time_score * 0.15

            # Interest alignment
            if interests and path.target_role.lower() in [i.lower() for i in interests]:
                score += 0.25
            elif interests:
                for interest in interests:
                    if interest.lower() in path.target_role.lower():
                        score += 0.15
                        break

            path.__dict__['_score'] = score

        return sorted(paths, key=lambda p: p.__dict__.get('_score', 0), reverse=True)