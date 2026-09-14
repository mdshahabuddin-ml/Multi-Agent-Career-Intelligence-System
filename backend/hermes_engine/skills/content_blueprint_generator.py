"""
Content Blueprint Generator - Transforms customer question + career context
into a structured ContentBlueprint.

The blueprint is the intermediate representation between raw context and
video generation. It captures what to teach, in what order, for whom,
and why — all grounded in the customer's original question.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from backend.config import settings
from backend.hermes_engine.memory.content_context import ContentContextResolver
from backend.hermes_engine.models.content_blueprint import ContentBlueprint

logger = logging.getLogger(__name__)


BLUEPRINT_PROMPT = """You are a career education curriculum designer.

The customer asked:
"{original_question}"

Their career context:
{career_context}

Content context:
Title: {title}
Body: {body_preview}

Based SOLELY on the customer's question above, create a structured learning blueprint.
The blueprint must be directly relevant to the question — do NOT invent unrelated topics.

For example, if the question is about becoming a Data Scientist, the topics should be
data science skills (Python, statistics, ML, etc.), NOT topics like marketing or design.

Return a JSON object (no markdown, no code blocks) with this exact format:
{{
  "original_question": "{original_question}",
  "target_topic": "The primary topic derived from the question (e.g. 'Data Science Skills')",
  "target_audience": "Who this is for (e.g. 'Aspiring Data Scientists')",
  "career_goal": "The career goal from the question or career context",
  "current_skills": ["skill1", "skill2", "skill3"],
  "learning_objectives": ["objective1", "objective2", "objective3", "objective4"],
  "key_concepts": ["concept1", "concept2", "concept3", "concept4", "concept5"],
  "topic_sequence": ["topic1", "topic2", "topic3", "topic4", "topic5"],
  "subtopics": {{
    "topic1": ["subtopic1a", "subtopic1b"],
    "topic2": ["subtopic2a", "subtopic2b"]
  }},
  "expected_outcome": "What the learner will achieve",
  "difficulty_level": "beginner/intermediate/advanced",
  "estimated_duration": "e.g. '4 weeks', '3 months'"
}}

Rules:
- target_topic MUST derive from the question, not be generic
- key_concepts must be specific to the topic (at least 5)
- topic_sequence must be a logical learning path (at least 4 items)
- subtopics must cover the main topics (at least 2 topics with subtopics)
- current_skills should come from career context if available
- difficulty_level should match the question complexity
- ALL fields must be filled in

Return ONLY the JSON object."""


class ContentBlueprintGenerator:
    """Generates a ContentBlueprint from resolved context.

    Usage:
        generator = ContentBlueprintGenerator(db)
        blueprint = generator.generate(content_id, user_id)
    """

    def __init__(self, db: Session):
        self.db = db

    def generate(self, content_id: int, user_id: int) -> ContentBlueprint:
        """Generate a blueprint for a content item.

        Args:
            content_id: The content item ID
            user_id: The owning user ID

        Returns:
            Validated ContentBlueprint

        Raises:
            ValueError: If context resolution fails or blueprint is invalid
        """
        # 1. Resolve context
        resolver = ContentContextResolver(self.db)
        context = resolver.resolve(content_id, user_id)

        # 2. Generate blueprint (LLM or mock)
        if settings.MOCK_VIDEO_GENERATION:
            blueprint = self._mock_blueprint(context)
        else:
            blueprint = self._llm_blueprint(context)

        # 3. Validate
        errors = blueprint.validate()
        if errors:
            raise ValueError(f"Blueprint validation failed: {'; '.join(errors)}")

        logger.info(
            "Generated blueprint for content %d: topic='%s', concepts=%d, sequence=%d",
            content_id,
            blueprint.target_topic,
            len(blueprint.key_concepts),
            len(blueprint.topic_sequence),
        )
        return blueprint

    def _llm_blueprint(self, context: Dict[str, Any]) -> ContentBlueprint:
        """Generate blueprint using LLM."""
        content_ctx = context.get("content", {})
        career_ctx = context.get("career", {})

        original_question = content_ctx.get("original_question") or content_ctx.get("title", "")

        # Format career context
        career_lines = []
        if career_ctx.get("target_role"):
            career_lines.append(f"Target role: {career_ctx['target_role']}")
        if career_ctx.get("skills"):
            career_lines.append(f"Existing skills: {', '.join(career_ctx['skills'][:10])}")
        if career_ctx.get("recent_experience"):
            roles = [f"{e.get('role', '')} at {e.get('company', '')}" for e in career_ctx["recent_experience"]]
            career_lines.append(f"Experience: {'; '.join(roles)}")
        if career_ctx.get("learning_goals"):
            goals = [g.get("title", "") for g in career_ctx["learning_goals"] if g.get("title")]
            career_lines.append(f"Learning goals: {', '.join(goals)}")
        career_context_str = "\n".join(career_lines) if career_lines else "No specific career context available."

        prompt = BLUEPRINT_PROMPT.format(
            original_question=original_question,
            career_context=career_context_str,
            title=content_ctx.get("title", ""),
            body_preview=content_ctx.get("body", "")[:500],
        )

        try:
            from backend.providers.llm.factory import LLMFactory
            provider = LLMFactory.create(
                provider="openai",
                model=settings.OPENAI_MODEL,
                api_key=settings.OPENAI_API_KEY,
            )
            import asyncio
            response = asyncio.get_event_loop().run_until_complete(
                provider.generate(prompt, max_tokens=2000)
            )
            text = response.get("text", "")
            data = json.loads(text.strip())
            return ContentBlueprint.from_dict(data)
        except Exception as e:
            logger.warning("LLM blueprint generation failed, using mock: %s", e)
            return self._mock_blueprint(context)

    def _mock_blueprint(self, context: Dict[str, Any]) -> ContentBlueprint:
        """Generate a mock blueprint derived from the question.

        Uses keyword analysis to derive relevant topics — never hardcoded.
        """
        content_ctx = context.get("content", {})
        career_ctx = context.get("career", {})

        question = content_ctx.get("original_question") or content_ctx.get("title", "")
        question_lower = question.lower()

        # Derive topic and concepts from the question
        topic, concepts, sequence, subtopics = self._analyze_question(question_lower)

        # Derive audience and goal
        audience = self._derive_audience(question_lower, career_ctx)
        goal = career_ctx.get("target_role", "") or self._derive_goal(question_lower)

        # Use career context for current skills
        current_skills = career_ctx.get("skills", [])[:8]

        # Derive difficulty from question complexity
        difficulty = self._derive_difficulty(question_lower)

        # Derive duration from topic scope
        duration = self._estimate_duration(len(sequence), difficulty)

        # Learning objectives from concepts
        objectives = [
            f"Understand core {c} concepts and principles"
            for c in concepts[:4]
        ]
        if len(objectives) < 4:
            objectives.append(f"Apply {topic} knowledge to real-world scenarios")
        objectives.append(f"Build a portfolio demonstrating {topic} proficiency")

        # Expected outcome
        outcome = f"Gain practical {topic} skills to {goal.lower()}" if goal else f"Gain practical {topic} skills"

        return ContentBlueprint(
            original_question=question,
            target_topic=topic,
            target_audience=audience,
            career_goal=goal,
            current_skills=current_skills,
            learning_objectives=objectives,
            key_concepts=concepts,
            topic_sequence=sequence,
            subtopics=subtopics,
            expected_outcome=outcome,
            difficulty_level=difficulty,
            estimated_duration=duration,
        )

    def _analyze_question(self, question: str) -> tuple:
        """Analyze question to derive topic, concepts, sequence, subtopics.

        Returns (topic, concepts, sequence, subtopics) all derived from question keywords.
        """
        # Topic extraction — look for "become a X", "learn X", "prepare for X", "X interview"
        topic = ""
        concept_pool = []

        # Data Science patterns
        if any(w in question for w in ["data scien", "data analy", "machine learn"]):
            topic = "Data Science"
            concept_pool = [
                "Python programming", "Statistics and probability", "Machine learning fundamentals",
                "Data visualization", "SQL and databases", "Deep learning",
                "Generative AI and LLMs", "Feature engineering", "Data cleaning and preprocessing",
                "Model evaluation and validation", "Portfolio development", "Business acumen",
            ]
        # Software Engineering patterns
        elif any(w in question for w in ["software eng", "software develop", "backend", "frontend", "full stack"]):
            topic = "Software Engineering"
            concept_pool = [
                "Programming fundamentals", "Data structures and algorithms", "System design",
                "Version control and Git", "Testing and quality assurance", "CI/CD pipelines",
                "Cloud platforms", "API design", "Database management", "Security best practices",
                "Agile methodologies", "Code review practices",
            ]
        # Interview preparation patterns
        elif any(w in question for w in ["interview", "hiring", "job prep", "career change"]):
            topic = "Technical Interview Preparation"
            concept_pool = [
                "Data structures and algorithms", "System design interviews", "Behavioral interview techniques",
                "Coding challenge strategies", "Resume optimization", "Portfolio presentation",
                "Salary negotiation", "Company research methods", "Mock interview practice",
                "Problem-solving frameworks", "Time management under pressure", "Communication skills",
            ]
        # Cybersecurity patterns
        elif any(w in question for w in ["cyber", "security", "information security", "network security"]):
            topic = "Cybersecurity"
            concept_pool = [
                "Network security fundamentals", "Operating system security", "Cryptography basics",
                "Vulnerability assessment", "Penetration testing", "Security compliance frameworks",
                "Incident response", "Threat analysis", "Security tools and monitoring",
                "Ethical hacking", "Risk management", "Security documentation",
            ]
        # Cloud/DevOps patterns
        elif any(w in question for w in ["cloud", "devops", "infrastructure", "aws", "azure"]):
            topic = "Cloud and DevOps"
            concept_pool = [
                "Cloud platform fundamentals", "Infrastructure as Code", "Container orchestration",
                "CI/CD pipeline design", "Monitoring and observability", "Security in cloud",
                "Cost optimization", "Serverless architecture", "Microservices patterns",
                "Networking and DNS", "Identity and access management", "Disaster recovery",
            ]
        # AI/ML patterns
        elif any(w in question for w in ["artificial intelligen", " ai ", " ml ", "deep learn", "neural"]):
            topic = "Artificial Intelligence and Machine Learning"
            concept_pool = [
                "Python for AI/ML", "Linear algebra and calculus", "Probability and statistics",
                "Supervised learning", "Unsupervised learning", "Deep learning architectures",
                "Natural language processing", "Computer vision", "Reinforcement learning",
                "MLOps and deployment", "Ethical AI", "Generative AI models",
            ]
        # Generic fallback — derive from any career-related keywords
        else:
            # Extract meaningful words from question
            words = [w for w in question.split() if len(w) > 3 and w not in (
                "what", "should", "learn", "become", "need", "know", "about",
                "your", "this", "that", "with", "from", "have", "will",
            )]
            topic = " ".join(words[:3]).title() if words else "Career Skills"
            concept_pool = [
                f"{w.title()} fundamentals" for w in words[:6]
            ] + [
                "Practical application", "Industry best practices",
                "Portfolio development", "Continuous learning strategies",
            ]

        # Build sequence (first 5-7 concepts as learning path)
        sequence = concept_pool[:min(7, len(concept_pool))]

        # Build subtopics (group concepts into 2-3 topic areas)
        mid = len(concept_pool) // 3 or 2
        subtopics = {
            "Foundations": concept_pool[:mid],
            "Core Skills": concept_pool[mid:mid*2],
            "Advanced Topics": concept_pool[mid*2:mid*3],
        }
        # Ensure at least 2 subtopic entries
        if len(subtopics) < 2:
            subtopics["Applied Practice"] = ["Hands-on projects", "Portfolio building"]

        return topic, concept_pool, sequence, subtopics

    def _derive_audience(self, question: str, career_ctx: Dict) -> str:
        """Derive target audience from question and career context."""
        target_role = career_ctx.get("target_role", "")
        if target_role:
            return f"Aspiring {target_role}"
        if any(w in question for w in ["beginner", "start", "new to"]):
            return "Beginners entering the field"
        if any(w in question for w in ["advance", "senior", "lead"]):
            return "Experienced professionals leveling up"
        return "Career changers and aspiring professionals"

    def _derive_goal(self, question: str) -> str:
        """Derive career goal from question."""
        if "become" in question:
            # Extract "become a X"
            parts = question.split("become a")
            if len(parts) > 1:
                goal_part = parts[1].strip().rstrip("?").strip()
                return f"Become a {goal_part}"
        if "prepare for" in question:
            parts = question.split("prepare for")
            if len(parts) > 1:
                goal_part = parts[1].strip().rstrip("?").strip()
                return f"Prepare for {goal_part}"
        return "Advance career in the target field"

    def _derive_difficulty(self, question: str) -> str:
        """Derive difficulty level from question."""
        if any(w in question for w in ["beginner", "start", "new", "basic", "intro"]):
            return "beginner"
        if any(w in question for w in ["advanced", "senior", "expert", "deep", "complex"]):
            return "advanced"
        return "intermediate"

    def _estimate_duration(self, num_topics: int, difficulty: str) -> str:
        """Estimate learning duration from topic count and difficulty."""
        base_weeks = max(4, num_topics * 2)
        if difficulty == "advanced":
            base_weeks = int(base_weeks * 1.5)
        elif difficulty == "beginner":
            base_weeks = int(base_weeks * 0.8)
        if base_weeks <= 4:
            return "4 weeks"
        if base_weeks <= 8:
            return "8 weeks"
        if base_weeks <= 12:
            return "3 months"
        return f"{base_weeks // 4} months"
