"""Platform captions for generated drafts.

Builds short, platform-sized captions extractively from the approved draft
text (lead + hashtags), so captions never introduce claims the draft does
not already contain. No LLM call is needed.
"""

from __future__ import annotations

import re
from typing import Dict, List

# Caption budgets per platform (characters, hashtags included).
CAPTION_LIMITS: Dict[str, int] = {
    "linkedin": 600,
    "instagram": 400,
    "facebook": 400,
    "youtube": 500,
    "youtube_shorts": 300,
    "tiktok": 300,
    "short": 300,
}

_HASHTAG_RE = re.compile(r"#[A-Za-z0-9_]+")


def extract_hashtags(text: str) -> List[str]:
    """Collect unique hashtags in order of appearance."""
    seen, tags = set(), []
    for tag in _HASHTAG_RE.findall(text or ""):
        lowered = tag.lower()
        if lowered not in seen:
            seen.add(lowered)
            tags.append(tag)
    return tags


def strip_hashtags(text: str) -> str:
    """Remove trailing empty or hashtag-only lines from a text."""
    lines = (text or "").strip().splitlines()
    while lines:
        remainder = _HASHTAG_RE.sub("", lines[-1]).strip()
        if remainder:
            break
        lines.pop()
    return "\n".join(lines).strip()


def build_caption(draft_text: str, platform: str, max_hashtags: int = 5) -> Dict[str, object]:
    """Build a caption for one platform from draft text.

    Returns ``{"text": ..., "hashtags": [...]}`` sized to the platform
    budget. The caption lead comes from the draft's own opening lines.
    """
    limit = CAPTION_LIMITS.get(platform, 300)
    hashtags = extract_hashtags(draft_text)[:max_hashtags]
    body = strip_hashtags(draft_text)

    lead_lines = [line.strip() for line in body.splitlines() if line.strip()]
    lead = " ".join(lead_lines[:2]).strip()
    if len(lead) > limit:
        cut = lead[: limit - 3].rsplit(" ", 1)[0]
        lead = (cut or lead[: limit - 3]) + "..."

    tag_block = " ".join(hashtags)
    if tag_block and len(lead) + 1 + len(tag_block) <= limit:
        text = f"{lead}\n{tag_block}" if lead else tag_block
    else:
        text = lead
    return {"text": text, "hashtags": hashtags}
