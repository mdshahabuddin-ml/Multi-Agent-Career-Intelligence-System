"""Prompt templates for Career-to-Content generation.

One template per supported content kind. Each builder receives a *brief* dict
produced by the intake stage (headline, skills, source highlight, audience)
and returns (system_prompt, user_prompt). Templates instruct the model to use
ONLY facts present in the brief (anti-hallucination) and to emit the
short-video schema (hook / beats / VO / on-screen / CTA) for scripts.
"""

from __future__ import annotations

from typing import Dict, Tuple

from backend.models.content_pipeline_run import ContentKind

LINKEDIN_POST = """You are a professional personal-branding writer. Write a LinkedIn post using ONLY the facts in the brief below. Do not invent employers, metrics, dates, or credentials.
Structure: hook line (1 sentence) + blank line + 2-4 short paragraphs + blank line + call to action + 3-5 hashtags on the final line. Keep it under 250 words, first person, confident but humble."""

EDUCATIONAL = """You are a technical educator. Write an educational post using ONLY the facts in the brief below. Do not invent statistics, studies, or quotes.
Structure: relatable hook + 3-5 numbered practical takeaways + one-line CTA question. Plain language, under 300 words."""

PROJECT_POST = """You are a developer advocate telling a build story. Write a project showcase post using ONLY the facts in the brief below. Do not invent features, users, metrics, or timelines.
Structure: problem (1-2 lines) + what you built + tech used + hardest challenge + result/lesson + repo/demo link placeholder if a URL was provided + CTA. Under 250 words."""

ACHIEVEMENT_POST = """You are writing a career milestone announcement using ONLY the facts in the brief below. Do not invent awards, ranks, or numbers.
Structure: the news in one line + 2-3 lines of backstory/gratitude + what is next + CTA. Warm, specific, under 180 words."""

CERTIFICATION_POST = """You are writing a certification announcement using ONLY the facts in the brief below. Do not invent scores, dates, or credential IDs.
Structure: credential earned (name + issuer) + why you pursued it + 1-2 key skills validated + credential link placeholder if a URL was provided + CTA. Under 180 words."""

CAREER_POST = """You are writing a career and learning update using ONLY the facts in the brief below. Do not invent roles, employers, metrics, timelines, or credentials.
Structure: hook (one line on what you are working toward or learning) + 2-3 short paragraphs on progress, lessons, or next steps + CTA question. First person, under 220 words."""

SHORT_VIDEO_SCRIPT = """You are a short-form video scriptwriter (Instagram Reels / Facebook Reels / YouTube Shorts). Use ONLY the facts in the brief below. Do not invent facts.
Emit EXACTLY these sections:
HOOK (0-3s): one spoken line under 12 words.
BEATS: 3-5 numbered beats, each with 'VO:' spoken line (under 25 words) and 'ON-SCREEN:' text overlay (under 8 words).
CTA (final 3s): one spoken line + on-screen text.
Total spoken content must fit ~60 seconds (~130-150 words). End with 5 hashtags on their own line."""

_TEMPLATES = {
    ContentKind.LINKEDIN_POST: LINKEDIN_POST,
    ContentKind.EDUCATIONAL: EDUCATIONAL,
    ContentKind.PROJECT_POST: PROJECT_POST,
    ContentKind.ACHIEVEMENT_POST: ACHIEVEMENT_POST,
    ContentKind.CERTIFICATION_POST: CERTIFICATION_POST,
    ContentKind.CAREER_POST: CAREER_POST,
    ContentKind.SHORT_VIDEO_SCRIPT: SHORT_VIDEO_SCRIPT,
}


def _render_brief(brief: Dict) -> str:
    lines = []
    for key in ("headline", "name", "target_role", "skills", "highlight", "audience"):
        value = brief.get(key)
        if not value:
            continue
        if isinstance(value, list):
            value = ", ".join(str(v) for v in value)
        lines.append(f"{key.replace('_', ' ').title()}: {value}")
    extra = brief.get("extra") or {}
    for key, value in extra.items():
        if value:
            lines.append(f"{str(key).replace('_', ' ').title()}: {value}")
    return "\n".join(lines)


def build_prompt(content_kind: ContentKind, brief: Dict) -> Tuple[str, str]:
    """Return (system_prompt, user_prompt) for a content kind + brief."""
    system = _TEMPLATES[content_kind]
    user = (
        "Write the content now.\n\nBRIEF (only usable facts):\n"
        f"{_render_brief(brief)}\n\nTarget platforms: "
        f"{', '.join(brief.get('platforms', [])) or 'general'}."
    )
    return system, user


def supported_kinds() -> list:
    return list(_TEMPLATES.keys())
