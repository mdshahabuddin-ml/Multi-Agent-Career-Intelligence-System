"""Platform-specific draft builder (formatting only, no publishing).

Converts one approved-topic draft text into per-platform draft shapes:

- LinkedIn → professional post (hook + body + CTA + hashtags, ≤3000)
- Instagram → short caption (+ structured script for Reels)
- Facebook → adapted post text + video description
- YouTube → title (≤100) + description (≤5000) + tags (+ script)

Everything is derived extractively from the draft text (plus caller-supplied
tags), so formatting can never invent claims. No network calls, no scraping.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from .platform_formatter import PlatformFormatter
from backend.content_engine.generation.captions import build_caption, extract_hashtags

YOUTUBE_TAG_LIMIT = 15

_SECTION_RE = re.compile(
    r"^(HOOK|BEATS?|CTA)(?:\s*\([^)]*\))?\s*:?\s*$", re.IGNORECASE
)
_BEAT_RE = re.compile(r"^(\d+)[.)]\s*(.*)$")
_VO_RE = re.compile(r"^VO\s*:\s*(.*)$", re.IGNORECASE)
_ONSCREEN_RE = re.compile(r"^ON[\s-]*SCREEN\s*:\s*(.*)$", re.IGNORECASE)


def parse_script_sections(text: str) -> Dict[str, Any]:
    """Parse a short-video script into hook/beats/cta structure.

    Falls back gracefully when section markers are absent.
    """
    lines = [(text or "").strip().splitlines()]
    flat = [line.strip() for line in lines[0] if line.strip()]
    sections: Dict[str, List[str]] = {"hook": [], "beats": [], "cta": []}
    current: Optional[str] = None
    for line in flat:
        marker = _SECTION_RE.match(line)
        if marker:
            name = marker.group(1).upper()
            current = "hook" if name == "HOOK" else ("cta" if name == "CTA" else "beats")
            continue
        if current:
            sections[current].append(line)
        elif not sections["hook"]:
            sections["hook"].append(line)

    beats: List[Dict[str, str]] = []
    current_beat: Optional[Dict[str, str]] = None
    for line in sections["beats"]:
        beat_match = _BEAT_RE.match(line)
        vo_match = _VO_RE.match(line)
        screen_match = _ONSCREEN_RE.match(line)
        if beat_match and not vo_match and not screen_match:
            if current_beat:
                beats.append(current_beat)
            rest = beat_match.group(2).strip()
            inner_vo = _VO_RE.match(rest)
            inner_screen = _ONSCREEN_RE.match(rest)
            current_beat = {
                "n": beat_match.group(1),
                "vo": (inner_vo.group(1).strip() if inner_vo else rest),
                "on_screen": (inner_screen.group(1).strip() if inner_screen else ""),
            }
        elif vo_match:
            if current_beat is None:
                current_beat = {"n": str(len(beats) + 1), "vo": "", "on_screen": ""}
            current_beat["vo"] = vo_match.group(1).strip()
        elif screen_match:
            if current_beat is None:
                current_beat = {"n": str(len(beats) + 1), "vo": "", "on_screen": ""}
            current_beat["on_screen"] = screen_match.group(1).strip()
    if current_beat:
        beats.append(current_beat)

    hook = " ".join(sections["hook"]).strip()
    cta_lines = " ".join(sections["cta"]).strip()
    if not hook:
        hook = flat[0] if flat else ""
    return {
        "hook": hook,
        "beats": beats,
        "cta": cta_lines,
        "has_structure": bool(sections["beats"] or sections["cta"]),
    }


def _clean_tags(hashtags: List[str], extra: Optional[List[str]] = None) -> List[str]:
    """Merge #tags and plain tags into a capped, deduped tag list."""
    seen, tags = set(), []
    for raw in list(hashtags or []) + list(extra or []):
        tag = raw.lstrip("#").strip()
        if tag and tag.lower() not in seen:
            seen.add(tag.lower())
            tags.append(tag)
        if len(tags) >= YOUTUBE_TAG_LIMIT:
            break
    return tags


class PlatformDraftBuilder:
    """Build per-platform draft variants from one draft text."""

    VIDEO_KINDS = {"short_video_script"}

    def __init__(self, formatter: Optional[PlatformFormatter] = None):
        self.formatter = formatter or PlatformFormatter()

    def build(
        self,
        draft_text: str,
        kind: str,
        platforms: List[str],
        extra_tags: Optional[List[str]] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """Return one draft dict per platform (text/caption preserved)."""
        text = (draft_text or "").strip()
        kind_value = getattr(kind, "value", kind)
        hashtags = extract_hashtags(text)
        script = parse_script_sections(text) if kind_value in self.VIDEO_KINDS else None

        variants: Dict[str, Dict[str, Any]] = {}
        for platform in platforms or []:
            formatted = self.formatter.format(text, platform)
            caption = build_caption(formatted, platform)
            if platform == "linkedin":
                variants[platform] = {
                    "kind": "post",
                    "text": formatted,
                    "caption": caption,
                    "hashtags": hashtags,
                }
            elif platform == "instagram":
                variants[platform] = {
                    "kind": "reel" if script else "post",
                    "text": formatted,
                    "caption": caption,
                    "hashtags": hashtags,
                    "script": script,
                }
            elif platform == "facebook":
                variants[platform] = {
                    "kind": "video" if script else "post",
                    "text": formatted,
                    "caption": caption,
                    "description": self._video_description(
                        formatted, caption, hashtags, platform),
                    "hashtags": hashtags,
                    "script": script,
                }
            elif platform in ("youtube", "youtube_shorts", "short", "tiktok"):
                first_line = (text.splitlines() or [""])[0]
                title = self.formatter.youtube_title(first_line or "Career update")
                variants[platform] = {
                    "kind": "short" if platform in ("youtube_shorts", "short", "tiktok") else "video",
                    "text": formatted,
                    "caption": caption,
                    "title": title,
                    "description": self._video_description(
                        formatted, caption, hashtags, platform, title=title),
                    "tags": _clean_tags(hashtags, extra_tags),
                    "hashtags": hashtags,
                    "script": script,
                }
            else:
                variants[platform] = {
                    "kind": "post",
                    "text": formatted,
                    "caption": caption,
                    "hashtags": hashtags,
                }
        return variants

    def _video_description(
        self,
        formatted: str,
        caption: Dict[str, Any],
        hashtags: List[str],
        platform: str,
        title: Optional[str] = None,
    ) -> str:
        """Longer description for video posts (lead + tags, within limit)."""
        limit = self.formatter._platform_limits.get(platform, 5000)
        lead = strip_lead(formatted)
        parts = [p for p in [title, lead] if p]
        body = "\n\n".join(parts)
        tag_block = " ".join(hashtags)
        if tag_block and len(body) + 2 + len(tag_block) <= limit:
            body = f"{body}\n\n{tag_block}" if body else tag_block
        if len(body) > limit:
            body = body[: limit - 3] + "..."
        return body


def strip_lead(formatted: str, max_chars: int = 600) -> str:
    """First substantive paragraph of a formatted text."""
    for paragraph in (formatted or "").split("\n\n"):
        cleaned = paragraph.strip()
        if cleaned:
            return cleaned if len(cleaned) <= max_chars else cleaned[: max_chars - 3] + "..."
    return (formatted or "").strip()[:max_chars]
