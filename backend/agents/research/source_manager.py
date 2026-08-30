import logging
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, field
from collections import defaultdict
from urllib.parse import urlparse
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class ManagedSource:
    """Managed source with metadata."""
    id: str
    url: str
    title: str
    snippet: str
    source_type: str
    domain: str
    credibility: float
    relevance: float
    author: Optional[str] = None
    published_date: Optional[str] = None
    content_hash: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    added_at: datetime = field(default_factory=datetime.utcnow)
    validation_status: str = "pending"  # pending, validated, rejected
    duplicate_of: Optional[str] = None


@dataclass
class SourceCollection:
    """Collection of managed sources."""
    sources: List[ManagedSource]
    total_count: int
    unique_domains: int
    source_types: Dict[str, int]
    avg_credibility: float
    avg_relevance: float
    duplicates_removed: int
    collected_at: datetime = field(default_factory=datetime.utcnow)


class SourceManager:
    """Manage sources: deduplication, validation, ranking."""

    def __init__(self):
        self.name = "source_manager"

        # Domain credibility tiers
        self.high_credibility_domains = {
            "arxiv.org", "pubmed.ncbi.nlm.nih.gov", "scholar.google.com",
            "github.com", "stackoverflow.com", "medium.com",
            "linkedin.com", "glassdoor.com", "indeed.com",
            "bls.gov", "census.gov", "oecd.org", "worldbank.org",
            "ieee.org", "acm.org", "nature.com", "science.org",
        }

        self.medium_credibility_domains = {
            "wikipedia.org", "reddit.com", "quora.com",
            "forbes.com", "bloomberg.com", "reuters.com",
            "techcrunch.com", "venturebeat.com", "theverge.com",
        }

        self.low_credibility_domains = {
            "pinterest.com", "tumblr.com", "buzzfeed.com",
        }

    async def process_sources(
        self,
        sources: List[Dict[str, Any]],
        query: str,
        max_sources: int = 50,
    ) -> SourceCollection:
        """Process raw sources into managed collection."""
        logger.info(f"Processing {len(sources)} raw sources")

        # Convert to ManagedSource objects
        managed = []
        for src in sources:
            managed_src = await self._create_managed_source(src)
            managed.append(managed_src)

        # Deduplicate
        deduplicated = self._deduplicate(managed)

        # Validate credibility
        validated = await self._validate_all(deduplicated)

        # Rank by relevance and credibility
        ranked = self._rank_sources(validated, query)

        # Limit to max_sources
        final_sources = ranked[:max_sources]

        # Calculate statistics
        collection = self._create_collection(final_sources, len(managed) - len(deduplicated))

        logger.info(f"Processed into {len(final_sources)} sources ({collection.duplicates_removed} duplicates removed)")
        return collection

    async def _create_managed_source(self, source: Dict[str, Any]) -> ManagedSource:
        """Create ManagedSource from raw source."""
        url = source.get("url", "")
        domain = self._extract_domain(url)

        # Generate content hash for deduplication
        content = f"{source.get('title', '')} {source.get('snippet', '')}"
        content_hash = hashlib.md5(content.encode()).hexdigest()[:16]

        return ManagedSource(
            id=source.get("id", content_hash),
            url=url,
            title=source.get("title", "Untitled"),
            snippet=source.get("snippet", ""),
            source_type=source.get("source_type", "web"),
            domain=domain,
            credibility=source.get("credibility", 0.5),
            relevance=source.get("relevance", 0.5),
            author=source.get("author"),
            published_date=source.get("published_date"),
            content_hash=content_hash,
            metadata=source.get("metadata", {}),
        )

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            # Remove www.
            if domain.startswith("www."):
                domain = domain[4:]
            return domain
        except Exception:
            return "unknown"

    def _deduplicate(self, sources: List[ManagedSource]) -> List[ManagedSource]:
        """Remove duplicate sources based on content hash and URL."""
        seen_hashes: Set[str] = set()
        seen_urls: Set[str] = set()
        unique = []
        duplicates = 0

        for src in sources:
            is_duplicate = False

            # Check content hash
            if src.content_hash in seen_hashes:
                is_duplicate = True
            # Check URL
            elif src.url and src.url in seen_urls:
                is_duplicate = True

            if is_duplicate:
                duplicates += 1
                logger.debug(f"Duplicate source: {src.url}")
            else:
                seen_hashes.add(src.content_hash)
                if src.url:
                    seen_urls.add(src.url)
                unique.append(src)

        logger.info(f"Deduplication: {len(sources)} -> {len(unique)} sources ({duplicates} removed)")
        return unique

    async def _validate_all(self, sources: List[ManagedSource]) -> List[ManagedSource]:
        """Validate all sources."""
        validated = []
        for src in sources:
            validated_src = await self._validate_source(src)
            validated.append(validated_src)
        return validated

    async def _validate_source(self, source: ManagedSource) -> ManagedSource:
        """Validate a single source."""
        # Assess domain credibility
        domain_cred = self._assess_domain_credibility(source.domain)

        # Assess content quality
        content_quality = self._assess_content_quality(source)

        # Assess recency
        recency_score = self._assess_recency(source.published_date)

        # Combined credibility score
        final_credibility = (
            source.credibility * 0.3 +
            domain_cred * 0.4 +
            content_quality * 0.2 +
            recency_score * 0.1
        )

        # Update source
        source.credibility = round(final_credibility, 3)
        source.domain = source.domain  # Keep domain
        source.metadata.update({
            "domain_credibility": round(domain_cred, 3),
            "content_quality": round(content_quality, 3),
            "recency_score": round(recency_score, 3),
            "validated_at": datetime.utcnow().isoformat(),
        })
        source.validation_status = "validated" if final_credibility > 0.3 else "rejected"

        return source

    def _assess_domain_credibility(self, domain: str) -> float:
        """Assess credibility based on domain."""
        if domain in self.high_credibility_domains:
            return 0.95
        if domain in self.medium_credibility_domains:
            return 0.7
        if domain in self.low_credibility_domains:
            return 0.3
        if domain.endswith((".edu", ".gov", ".org")):
            return 0.85
        if domain.endswith(".com"):
            return 0.6
        return 0.4

    def _assess_content_quality(self, source: ManagedSource) -> float:
        """Assess content quality."""
        score = 0.3

        # Title quality
        title = source.title
        if title and len(title) > 15:
            score += 0.1
        if title and len(title) > 50:
            score += 0.05

        # Snippet quality
        snippet = source.snippet
        if snippet and len(snippet) > 100:
            score += 0.2
        elif snippet and len(snippet) > 50:
            score += 0.1

        # Has author
        if source.author:
            score += 0.1

        # Has date
        if source.published_date:
            score += 0.1

        # Source type bonus
        if source.source_type in ["academic", "job_market"]:
            score += 0.1

        return min(score, 1.0)

    def _assess_recency(self, published_date: Optional[str]) -> float:
        """Assess recency score (1.0 = very recent)."""
        if not published_date:
            return 0.5

        try:
            from datetime import datetime, timezone
            pub_dt = datetime.fromisoformat(published_date.replace("Z", "+00:00"))
            if pub_dt.tzinfo is None:
                pub_dt = pub_dt.replace(tzinfo=timezone.utc)

            now = datetime.now(timezone.utc)
            days_old = (now - pub_dt).days

            if days_old < 7:
                return 1.0
            elif days_old < 30:
                return 0.9
            elif days_old < 90:
                return 0.7
            elif days_old < 180:
                return 0.5
            elif days_old < 365:
                return 0.3
            else:
                return 0.1
        except Exception:
            return 0.5

    def _rank_sources(
        self,
        sources: List[ManagedSource],
        query: str,
    ) -> List[ManagedSource]:
        """Rank sources by combined relevance and credibility."""
        query_keywords = set(query.lower().split())

        for src in sources:
            # Calculate keyword relevance
            text = f"{src.title} {src.snippet}".lower()
            text_keywords = set(text.split())
            overlap = query_keywords & text_keywords
            keyword_relevance = len(overlap) / len(query_keywords) if query_keywords else 0

            # Combined score
            src.relevance = round(
                src.relevance * 0.6 + keyword_relevance * 0.4, 3
            )

            # Final ranking score
            src.metadata["ranking_score"] = round(
                src.credibility * 0.5 + src.relevance * 0.5, 3
            )

        # Sort by ranking score descending
        sources.sort(key=lambda s: s.metadata.get("ranking_score", 0), reverse=True)
        return sources

    def _create_collection(
        self,
        sources: List[ManagedSource],
        duplicates_removed: int,
    ) -> SourceCollection:
        """Create source collection with statistics."""
        if not sources:
            return SourceCollection(
                sources=[],
                total_count=0,
                unique_domains=0,
                source_types={},
                avg_credibility=0.0,
                avg_relevance=0.0,
                duplicates_removed=duplicates_removed,
            )

        domains = set(s.domain for s in sources)
        source_types = defaultdict(int)
        for s in sources:
            source_types[s.source_type] += 1

        avg_cred = sum(s.credibility for s in sources) / len(sources)
        avg_rel = sum(s.relevance for s in sources) / len(sources)

        return SourceCollection(
            sources=sources,
            total_count=len(sources),
            unique_domains=len(domains),
            source_types=dict(source_types),
            avg_credibility=round(avg_cred, 3),
            avg_relevance=round(avg_rel, 3),
            duplicates_removed=duplicates_removed,
        )

    async def get_sources_by_type(
        self,
        collection: SourceCollection,
        source_type: str,
    ) -> List[ManagedSource]:
        """Get sources filtered by type."""
        return [s for s in collection.sources if s.source_type == source_type]

    async def get_top_sources(
        self,
        collection: SourceCollection,
        count: int = 10,
    ) -> List[ManagedSource]:
        """Get top N sources by ranking score."""
        return collection.sources[:count]

    async def export_sources(
        self,
        collection: SourceCollection,
        format: str = "json",
    ) -> Any:
        """Export sources in various formats."""
        if format == "json":
            return [
                {
                    "id": s.id,
                    "url": s.url,
                    "title": s.title,
                    "snippet": s.snippet,
                    "source_type": s.source_type,
                    "domain": s.domain,
                    "credibility": s.credibility,
                    "relevance": s.relevance,
                    "author": s.author,
                    "published_date": s.published_date,
                    "metadata": s.metadata,
                }
                for s in collection.sources
            ]
        elif format == "csv":
            import csv
            import io
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["ID", "URL", "Title", "Type", "Domain", "Credibility", "Relevance", "Author", "Date"])
            for s in collection.sources:
                writer.writerow([
                    s.id, s.url, s.title, s.source_type, s.domain,
                    s.credibility, s.relevance, s.author or "", s.published_date or ""
                ])
            return output.getvalue()
        return collection.sources