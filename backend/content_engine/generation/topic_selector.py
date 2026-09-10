"""Topic selection for Career-to-Content generation.

Derives post topics deterministically from the intake brief so every
suggested topic is grounded in the user's actual material (skills,
projects, certifications, achievements, research, learning goals).
No LLM call is needed: selection is extraction, not prose.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.models.content_pipeline_run import ContentKind


def _first_text(*values: Any) -> str:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def suggest_topics(brief: Dict[str, Any], max_topics: int = 5) -> List[Dict[str, Any]]:
    """Suggest grounded content topics from a brief.

    Each suggestion carries the source section it came from plus a
    recommended content kind, so downstream stages stay traceable.
    """
    topics: List[Dict[str, Any]] = []
    extra = brief.get("extra") or {}
    skills = brief.get("skills") or []
    highlight = _first_text(brief.get("highlight"))

    if highlight:
        topics.append({
            "topic": highlight[:140],
            "angle": "story",
            "source": "highlight",
            "suggested_kind": ContentKind.LINKEDIN_POST.value,
        })

    for skill in skills[:3]:
        topics.append({
            "topic": f"What learning {skill} taught me",
            "angle": "lesson",
            "source": "skills",
            "suggested_kind": ContentKind.EDUCATIONAL.value,
        })

    project_url = (brief.get("extra") or {}).get("url")
    if project_url and highlight:
        topics.append({
            "topic": f"How I built {highlight[:100]}",
            "angle": "build-story",
            "source": "project",
            "suggested_kind": ContentKind.PROJECT_POST.value,
        })

    if extra.get("issuer"):
        topics.append({
            "topic": f"Earning {highlight[:100]}",
            "angle": "announcement",
            "source": "certification",
            "suggested_kind": ContentKind.CERTIFICATION_POST.value,
        })

    if brief.get("target_role"):
        topics.append({
            "topic": f"My path toward {brief['target_role']}",
            "angle": "journey",
            "source": "target_role",
            "suggested_kind": ContentKind.CAREER_POST.value,
        })

    if brief.get("extra", {}).get("topic"):
        topics.append({
            "topic": f"Key findings: {extra['topic'][:100]}",
            "angle": "insights",
            "source": "research",
            "suggested_kind": ContentKind.EDUCATIONAL.value,
        })

    # Deduplicate while preserving order, then cap.
    seen, unique = set(), []
    for topic in topics:
        key = (topic["topic"], topic["suggested_kind"])
        if key not in seen:
            seen.add(key)
            unique.append(topic)
    return unique[:max_topics]


def pick_topic(
    brief: Dict[str, Any],
    requested: Optional[str] = None,
    max_topics: int = 5,
) -> Dict[str, Any]:
    """Return the requested topic if given, else the first suggestion.

    A caller-supplied topic is still recorded with its provenance so the
    run record shows whether the topic was suggested or supplied.
    """
    suggestions = suggest_topics(brief, max_topics=max_topics)
    if requested and requested.strip():
        return {
            "topic": requested.strip(),
            "angle": "supplied",
            "source": "caller",
            "suggested_kind": None,
            "suggestions": suggestions,
        }
    if not suggestions:
        return {
            "topic": _first_text(brief.get("headline"), brief.get("target_role"), "career update"),
            "angle": "fallback",
            "source": "brief",
            "suggested_kind": ContentKind.CAREER_POST.value,
            "suggestions": suggestions,
        }
    first = dict(suggestions[0])
    first["suggestions"] = suggestions
    return first
