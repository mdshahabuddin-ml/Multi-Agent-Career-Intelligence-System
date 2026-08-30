from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum as PyEnum
from urllib.parse import urlparse
import hashlib
import logging

from backend.research_engine.state.research_context import (
    SourceMetadata, ResearchSourceType
)

logger = logging.getLogger(__name__)


class SourceStatus(str, PyEnum):
    """Status of a source."""
    DISCOVERED = "discovered"
    FETCHING = "fetching"
    FETCHED = "fetched"
    PARSED = "parsed"
    FAILED = "failed"
    EXCLUDED = "excluded"


@dataclass
class SourceRecord:
    """Complete record of a source."""
    metadata: SourceMetadata
    status: SourceStatus = SourceStatus.DISCOVERED
    content: Optional[str] = None
    content_hash: Optional[str] = None
    fetch_error: Optional[str] = None
    fetch_time_ms: int = 0
    parse_error: Optional[str] = None
    extracted_at: Optional[datetime] = None
    chunks: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metadata": self.metadata.to_dict(),
            "status": self.status.value,
            "content_length": len(self.content) if self.content else 0,
            "content_hash": self.content_hash,
            "fetch_error": self.fetch_error,
            "fetch_time_ms": self.fetch_time_ms,
            "parse_error": self.parse_error,
            "extracted_at": self.extracted_at.isoformat() if self.extracted_at else None,
            "chunk_count": len(self.chunks),
        }


class SourceManager:
    """Manage research sources throughout the pipeline."""

    def __init__(self):
        self._sources: Dict[str, SourceRecord] = {}  # keyed by URL
        self._by_research: Dict[int, List[str]] = {}  # research_id -> list of URLs

    def add_source(
        self,
        research_id: int,
        url: str,
        title: str,
        source_type: ResearchSourceType,
        **kwargs
    ) -> SourceRecord:
        """Add a new source."""
        # Normalize URL
        normalized_url = self._normalize_url(url)

        # Check if already exists
        if normalized_url in self._sources:
            existing = self._sources[normalized_url]
            if research_id not in self._by_research.get(research_id, []):
                self._by_research.setdefault(research_id, []).append(normalized_url)
            return existing

        # Extract domain
        domain = self._extract_domain(normalized_url)

        # Create metadata
        metadata = SourceMetadata(
            url=normalized_url,
            title=title,
            source_type=source_type,
            domain=domain,
            **kwargs
        )

        # Create record
        record = SourceRecord(metadata=metadata)
        self._sources[normalized_url] = record

        # Index by research
        self._by_research.setdefault(research_id, []).append(normalized_url)

        return record

    def get_source(self, url: str) -> Optional[SourceRecord]:
        """Get source by URL."""
        normalized = self._normalize_url(url)
        return self._sources.get(normalized)

    def get_sources_for_research(self, research_id: int) -> List[SourceRecord]:
        """Get all sources for a research."""
        urls = self._by_research.get(research_id, [])
        return [self._sources[u] for u in urls if u in self._sources]

    def update_status(self, url: str, status: SourceStatus, **kwargs):
        """Update source status."""
        record = self.get_source(url)
        if record:
            record.status = status
            for key, value in kwargs.items():
                if hasattr(record, key):
                    setattr(record, key, value)

    def update_content(self, url: str, content: str, fetch_time_ms: int = 0):
        """Update source content."""
        record = self.get_source(url)
        if record:
            record.content = content
            record.content_hash = self._hash_content(content)
            record.fetch_time_ms = fetch_time_ms
            record.status = SourceStatus.FETCHED
            record.extracted_at = datetime.utcnow()

            # Update metadata
            record.metadata.word_count = len(content.split())
            record.metadata.content_hash = record.content_hash

    def update_parsed(self, url: str, chunks: List[Dict[str, Any]], parse_error: Optional[str] = None):
        """Update parsed content."""
        record = self.get_source(url)
        if record:
            record.chunks = chunks
            if parse_error:
                record.parse_error = parse_error
                record.status = SourceStatus.FAILED
            else:
                record.status = SourceStatus.PARSED

    def exclude_source(self, url: str, reason: str):
        """Exclude a source from results."""
        record = self.get_source(url)
        if record:
            record.status = SourceStatus.EXCLUDED
            record.fetch_error = reason

    def get_ready_sources(self, research_id: int) -> List[SourceRecord]:
        """Get sources ready for processing (fetched and parsed)."""
        sources = self.get_sources_for_research(research_id)
        return [
            s for s in sources
            if s.status in [SourceStatus.FETCHED, SourceStatus.PARSED]
        ]

    def get_source_stats(self, research_id: int) -> Dict[str, Any]:
        """Get source statistics for a research."""
        sources = self.get_sources_for_research(research_id)
        if not sources:
            return {"total": 0}

        status_counts = {}
        type_counts = {}
        total_words = 0
        total_fetch_time = 0

        for s in sources:
            status_counts[s.status.value] = status_counts.get(s.status.value, 0) + 1
            type_counts[s.metadata.source_type.value] = type_counts.get(s.metadata.source_type.value, 0) + 1
            total_words += s.metadata.word_count
            total_fetch_time += s.fetch_time_ms

        return {
            "total": len(sources),
            "by_status": status_counts,
            "by_type": type_counts,
            "total_words": total_words,
            "total_fetch_time_ms": total_fetch_time,
            "avg_fetch_time_ms": round(total_fetch_time / len(sources)) if sources else 0,
        }

    def _normalize_url(self, url: str) -> str:
        """Normalize URL for deduplication."""
        # Remove fragment, normalize scheme
        parsed = urlparse(url)
        normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        if parsed.query:
            normalized += f"?{parsed.query}"
        return normalized.lower()

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        parsed = urlparse(url)
        return parsed.netloc.lower().replace("www.", "")

    def _hash_content(self, content: str) -> str:
        """Generate content hash for deduplication."""
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def deduplicate_sources(self, research_id: int) -> int:
        """Remove duplicate sources based on content hash."""
        sources = self.get_sources_for_research(research_id)
        seen_hashes = set()
        removed = 0

        for record in sources:
            if record.content_hash:
                if record.content_hash in seen_hashes:
                    self.exclude_source(record.metadata.url, "Duplicate content")
                    removed += 1
                else:
                    seen_hashes.add(record.content_hash)

        return removed