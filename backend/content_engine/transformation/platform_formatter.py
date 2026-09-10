"""
Platform Formatter - Formats content for different platforms.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


class PlatformFormatter:
    """
    Formats content for different social media platforms.
    """

    def __init__(self):
        self._platform_limits = {
            "twitter": 280,
            "linkedin": 3000,
            "instagram": 2200,
            "facebook": 63206,
            # Short-form video captions/descriptions (pipeline addition).
            "youtube": 5000,      # video description limit (titles handled separately)
            "youtube_shorts": 5000,
            "tiktok": 4000,       # caption limit incl. hashtags
            "short": 2200,        # generic short-video caption (Reels parity)
        }
        self._youtube_title_limit = 100

    def youtube_title(self, title: str) -> str:
        """Trim a YouTube/Shorts title to the 100-char platform limit."""
        title = (title or "").strip()
        if len(title) > self._youtube_title_limit:
            return title[: self._youtube_title_limit - 3] + "..."
        return title

    def format(
        self,
        content: str,
        platform: str,
        **kwargs: Any,
    ) -> str:
        """Format content for a platform."""
        limit = self._platform_limits.get(platform, 2000)
        if len(content) > limit:
            return content[:limit - 3] + "..."
        return content
