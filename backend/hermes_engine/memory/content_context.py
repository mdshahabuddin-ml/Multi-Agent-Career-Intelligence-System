"""
Content Context Resolver - Bridges Content Items to Hermes context.

Resolves a Content Item ID into the full context Hermes needs:
- Original customer question (primary intent)
- Content title, body, tags
- User profile context (target role, skills, experience)
- Career goal context (learning plans, certifications)
- Existing research/context

Enforces user isolation: every query is scoped to the requesting user_id.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from backend.models.content import Content
from .career_context import CareerContextProvider

logger = logging.getLogger(__name__)


class ContentContextResolver:
    """Resolves a Content Item into the full context dict Hermes needs.

    Usage:
        resolver = ContentContextResolver(db)
        ctx = resolver.resolve(content_id, user_id)
    """

    def __init__(self, db: Session):
        self.db = db
        self._career_provider = CareerContextProvider(db)

    def resolve(self, content_id: int, user_id: int) -> Dict[str, Any]:
        """Resolve a content item into a full Hermes context dict.

        Args:
            content_id: The content item ID
            user_id: The owning user ID (enforces isolation)

        Returns:
            Dict with keys: original_question, title, body, tags,
            career_context, profile_summary

        Raises:
            ValueError: If content not found or user_id doesn't match
        """
        # 1. Fetch content (enforces user isolation)
        content = self.db.query(Content).filter(
            Content.id == content_id,
            Content.user_id == user_id,
        ).first()
        if not content:
            raise ValueError(f"Content {content_id} not found for user {user_id}")

        # 2. Build content section
        content_section = {
            "content_id": content.id,
            "original_question": content.original_question,
            "title": content.title,
            "body": content.body[:3000] if content.body else "",
            "tags": content.tags_json or [],
            "status": content.status,
            "content_type": content.content_type,
        }

        # 3. Build career context section (profile, skills, goals, research)
        career_section = self._resolve_career_context(user_id)

        # 4. Assemble full context
        context = {
            "content": content_section,
            "career": career_section,
        }

        logger.info(
            "Resolved context for content %d (user %d): question=%s, career_keys=%s",
            content_id,
            user_id,
            bool(content.original_question),
            list(career_section.keys()),
        )
        return context

    def _resolve_career_context(self, user_id: int) -> Dict[str, Any]:
        """Resolve career context, returning empty dict on error.

        Never raises — career context is supplementary, not blocking.
        """
        try:
            snapshot = self._career_provider.snapshot(user_id)
            return self._compact_snapshot(snapshot)
        except Exception as e:
            logger.warning("Career context unavailable for user %d: %s", user_id, e)
            return {}

    def _compact_snapshot(self, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """Extract the most relevant career context for video generation.

        Keeps only what matters for content creation: target role, key skills,
        recent experience, active learning plans, and research summary.
        """
        profile = snapshot.get("profile") or {}
        skills = snapshot.get("skills") or []
        experience = snapshot.get("experience") or []
        learning = snapshot.get("learning") or []
        research = snapshot.get("research") or []

        # Extract skill names (top 15)
        skill_names = [s.get("name", "") for s in skills[:15] if s.get("name")]

        # Extract recent experience (last 3 roles)
        recent_experience = []
        for exp in experience[-3:]:
            recent_experience.append({
                "role": exp.get("role", ""),
                "company": exp.get("company", ""),
            })

        # Extract active learning goals
        learning_goals = []
        for plan in learning[:3]:
            if plan.get("title"):
                learning_goals.append({
                    "title": plan["title"],
                    "target_role": plan.get("target_role", ""),
                    "progress": plan.get("progress", 0),
                })

        # Extract latest research summary
        latest_research = []
        for r in research[:2]:
            if r.get("query"):
                latest_research.append({
                    "query": r["query"],
                    "summary": r.get("summary", "")[:500],
                    "key_findings": r.get("key_findings", [])[:5],
                })

        return {
            "target_role": profile.get("target_role", ""),
            "headline": profile.get("headline", ""),
            "skills": skill_names,
            "recent_experience": recent_experience,
            "learning_goals": learning_goals,
            "latest_research": latest_research,
        }

    def get_intent_summary(self, context: Dict[str, Any]) -> str:
        """Extract a human-readable intent summary from resolved context.

        Returns the original question if present, otherwise falls back to title.
        This is the PRIMARY intent that should drive all downstream generation.
        """
        content = context.get("content", {})
        return content.get("original_question") or content.get("title") or ""
