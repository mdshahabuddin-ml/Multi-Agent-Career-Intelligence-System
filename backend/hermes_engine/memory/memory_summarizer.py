"""
Memory Summarizer - Summarizes memory content.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class MemorySummarizer:
    """
    Summarizes memory content for context compression.
    """

    def __init__(self):
        self._max_summary_length = 200

    def summarize(
        self,
        memories: List[Dict[str, Any]],
        max_length: Optional[int] = None,
    ) -> str:
        """
        Summarize a list of memories.
        """
        if not memories:
            return ""

        max_len = max_length or self._max_summary_length

        # Simple extractive summarization
        summaries = []
        total_length = 0

        for memory in memories:
            content = str(memory.get("content", ""))
            if total_length + len(content) > max_len:
                break
            summaries.append(content)
            total_length += len(content)

        return " | ".join(summaries)

    def compress_conversation(
        self,
        messages: List[Dict[str, Any]],
        max_messages: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Compress conversation history.
        """
        if len(messages) <= max_messages:
            return messages

        # Keep first 2 and last max_messages-2
        return messages[:2] + messages[-(max_messages - 2):]
