"""
Topic analysis: historical rows → per-topic measured performance.

Deterministic and dependency-free (no LLM, no network):
- Topics come from ``hashtags`` when present, else keyword tokens from
  ``title`` after lowercasing, stopword removal and de-duplication.
- A post contributes to every topic it mentions; engagement is attributed
  in full to each (documented, not split — splitting would fabricate
  precision the data does not have).
- ``None`` (official-API-unsupported) metrics are excluded, never zeroed.
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any, Dict, List, Optional

from backend.hermes.optimization.schemas import TopicPerformance

_STOPWORDS = frozenset({
    "the", "a", "an", "and", "or", "for", "with", "how", "what", "why",
    "your", "you", "our", "tips", "guide", "part", "new", "top", "best",
    "get", "getting", "into", "from", "that", "this", "these", "those",
    "are", "is", "to", "in", "on", "of", "vs",
})

_TOKEN_RE = re.compile(r"[a-z][a-z0-9+#-]*")


def _norm_token(raw: str) -> str:
    token = raw.strip().lower().lstrip("#")
    return token


def extract_topics(row: Dict[str, Any], max_topics: int = 4) -> List[str]:
    """Extract up to ``max_topics`` normalized topic tokens for one post row."""
    topics: List[str] = []
    seen: set[str] = set()

    def _add(token: str) -> None:
        token = _norm_token(token)
        if len(token) < 3 or token in _STOPWORDS or token in seen:
            return
        seen.add(token)
        topics.append(token)

    for tag in row.get("hashtags") or []:
        if len(topics) >= max_topics:
            break
        _add(str(tag))
    if len(topics) < max_topics:
        for match in _TOKEN_RE.findall(str(row.get("title") or "").lower()):
            if len(topics) >= max_topics:
                break
            _add(match)
    return topics


def _num(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def analyse_topics(rows: List[Dict[str, Any]]) -> List[TopicPerformance]:
    """Aggregate measured performance per topic, best first.

    Ranking: avg engagement rate (needs ≥1 measured post with a rate),
    then total interactions. Topics with zero measured posts are kept
    (transparency) but sort last.
    """
    buckets: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {"post_ids": [], "rates": [], "interactions": 0,
                 "measured": 0, "platforms": set()}
    )
    for row in rows:
        topics = extract_topics(row)
        if not topics:
            topics = ["untagged"]
        likes = _num(row.get("likes")) or 0.0
        comments = _num(row.get("comments")) or 0.0
        shares = _num(row.get("shares")) or 0.0
        interactions = likes + comments + shares
        measured = any(row.get(k) is not None for k in ("likes", "comments", "shares", "views", "impressions"))
        rate = _num(row.get("engagement_rate"))
        for topic in topics:
            bucket = buckets[topic]
            bucket["post_ids"].append(row.get("content_id"))
            bucket["interactions"] += interactions
            bucket["platforms"].add(str(row.get("platform", "unknown")))
            if measured:
                bucket["measured"] += 1
                if rate is not None:
                    bucket["rates"].append(rate)

    out: List[TopicPerformance] = []
    for topic, bucket in buckets.items():
        rates = bucket["rates"]
        out.append(TopicPerformance(
            topic=topic,
            posts=len(bucket["post_ids"]),
            measured_posts=bucket["measured"],
            avg_engagement_rate=round(sum(rates) / len(rates), 2) if rates else None,
            total_interactions=int(bucket["interactions"]),
            post_ids=[int(pid) for pid in bucket["post_ids"] if pid is not None],
            platforms=sorted(bucket["platforms"]),
        ))

    def _key(item: TopicPerformance) -> tuple:
        return (
            item.measured_posts > 0,
            item.avg_engagement_rate is not None,
            item.avg_engagement_rate or -1.0,
            item.total_interactions,
        )

    return sorted(out, key=_key, reverse=True)
