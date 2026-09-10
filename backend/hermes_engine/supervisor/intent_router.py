"""
Intent Router - Classifies user intents for agent routing.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from enum import Enum


class Intent(str, Enum):
    """Supported intents."""
    RESEARCH = "research"
    CAREER = "career"
    INTERVIEW = "interview"
    APPLICATION = "application"
    RESUME = "resume"
    CONTENT = "content"
    AUTOMATION = "automation"
    MEMORY = "memory"
    SKILLS = "skills"
    GENERAL = "general"


# Intent keywords mapping
INTENT_KEYWORDS: Dict[Intent, List[str]] = {
    Intent.RESEARCH: ["research", "analyze", "investigate", "study", "report", "data"],
    Intent.CAREER: ["career", "path", "growth", "skill", "gap", "learning", "plan"],
    Intent.INTERVIEW: ["interview", "question", "mock", "practice", "answer", "star"],
    Intent.APPLICATION: ["application", "apply", "job", "submit", "resume", "cover"],
    Intent.RESUME: ["resume", "cv", "profile", "experience", "project"],
    Intent.CONTENT: ["content", "post", "article", "blog", "social", "caption"],
    Intent.AUTOMATION: ["automate", "schedule", "cron", "trigger", "workflow"],
    Intent.MEMORY: ["remember", "recall", "memory", "context", "history"],
    Intent.SKILLS: ["skill", "learn", "course", "training", "certificate"],
}


class IntentRouter:
    """
    Routes user intents to appropriate agents based on content analysis.
    """

    def __init__(self):
        self._custom_mappings: Dict[str, Intent] = {}

    def classify(
        self,
        task: str,
        input_data: Optional[Dict[str, Any]] = None,
    ) -> Intent:
        """
        Classify the intent of a task.
        
        Args:
            task: Task description
            input_data: Additional input data
            
        Returns:
            Classified Intent
        """
        task_lower = task.lower()
        input_str = str(input_data or {}).lower()
        combined = f"{task_lower} {input_str}"

        # Check custom mappings first
        for keyword, intent in self._custom_mappings.items():
            if keyword in combined:
                return intent

        # Score each intent
        scores: Dict[Intent, int] = {}
        for intent, keywords in INTENT_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in combined)
            if score > 0:
                scores[intent] = score

        if scores:
            return max(scores, key=scores.get)

        return Intent.GENERAL

    def add_mapping(self, keyword: str, intent: Intent) -> None:
        """Add a custom keyword-intent mapping."""
        self._custom_mappings[keyword] = intent

    def get_supported_intents(self) -> List[str]:
        """Get list of supported intents."""
        return [intent.value for intent in Intent]
