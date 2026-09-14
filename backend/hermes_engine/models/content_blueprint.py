"""
Content Blueprint schema - structured representation of a learning path
derived from a customer's question and career context.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass
class ContentBlueprint:
    """Structured blueprint for content generation, derived from a customer question.

    Grounded in the original question — never invents unrelated topics.
    """

    original_question: str = ""
    target_topic: str = ""
    target_audience: str = ""
    career_goal: str = ""
    current_skills: List[str] = field(default_factory=list)
    learning_objectives: List[str] = field(default_factory=list)
    key_concepts: List[str] = field(default_factory=list)
    topic_sequence: List[str] = field(default_factory=list)
    subtopics: Dict[str, List[str]] = field(default_factory=dict)
    expected_outcome: str = ""
    difficulty_level: str = ""
    estimated_duration: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict for storage in metadata_json."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContentBlueprint":
        """Deserialize from dict."""
        if not data:
            return cls()
        return cls(
            original_question=data.get("original_question", ""),
            target_topic=data.get("target_topic", ""),
            target_audience=data.get("target_audience", ""),
            career_goal=data.get("career_goal", ""),
            current_skills=data.get("current_skills", []),
            learning_objectives=data.get("learning_objectives", []),
            key_concepts=data.get("key_concepts", []),
            topic_sequence=data.get("topic_sequence", []),
            subtopics=data.get("subtopics", {}),
            expected_outcome=data.get("expected_outcome", ""),
            difficulty_level=data.get("difficulty_level", ""),
            estimated_duration=data.get("estimated_duration", ""),
        )

    def validate(self) -> List[str]:
        """Validate the blueprint. Returns list of errors (empty = valid).

        Rejects empty or incomplete blueprints.
        """
        errors = []

        if not self.original_question.strip():
            errors.append("original_question is required")
        if not self.target_topic.strip():
            errors.append("target_topic is required — must derive from the question")
        if not self.target_audience.strip():
            errors.append("target_audience is required")
        if not self.key_concepts or len(self.key_concepts) < 3:
            errors.append("key_concepts must have at least 3 items")
        if not self.topic_sequence or len(self.topic_sequence) < 2:
            errors.append("topic_sequence must have at least 2 items")
        if not self.learning_objectives or len(self.learning_objectives) < 2:
            errors.append("learning_objectives must have at least 2 items")
        if not self.difficulty_level.strip():
            errors.append("difficulty_level is required")
        if not self.expected_outcome.strip():
            errors.append("expected_outcome is required")

        # Check topic coherence: target_topic should relate to original_question
        if self.original_question and self.target_topic:
            question_words = set(self.original_question.lower().split())
            topic_words = set(self.target_topic.lower().split())
            # Remove common filler words
            stopwords = {"a", "an", "the", "in", "on", "for", "to", "of", "and", "or", "is", "what", "how", "i", "my", "should", "learn", "become"}
            question_content = question_words - stopwords
            topic_content = topic_words - stopwords
            overlap = question_content & topic_content
            if not overlap:
                errors.append(
                    f"target_topic '{self.target_topic}' appears unrelated to the question — no overlapping keywords"
                )

        return errors
