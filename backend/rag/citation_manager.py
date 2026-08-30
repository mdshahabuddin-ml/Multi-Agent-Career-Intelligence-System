from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass, field
from enum import Enum as PyEnum
from datetime import datetime
import logging
import re

from backend.research_engine.state.research_context import SourceMetadata

logger = logging.getLogger(__name__)


class CitationStyle(str, PyEnum):
    """Citation styles."""
    APA = "apa"
    MLA = "mla"
    CHICAGO = "chicago"
    IEEE = "ieee"
    HARVARD = "harvard"
    SIMPLE = "simple"
    NUMBERED = "numbered"


@dataclass
class Citation:
    """A formatted citation."""
    index: int
    source: SourceMetadata
    style: CitationStyle
    formatted: str
    in_text: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "index": self.index,
            "source_url": self.source.url,
            "source_title": self.source.title,
            "source_type": self.source.source_type.value,
            "formatted": self.formatted,
            "in_text": self.in_text,
        }


@dataclass
class CitationContext:
    """Context for citation generation."""
    text: str
    source_ids: List[str]
    style: CitationStyle = CitationStyle.NUMBERED
    include_doi: bool = False
    include_url: bool = True
    max_authors: int = 3


class CitationManager:
    """Manage citations for RAG responses."""

    def __init__(self, default_style: CitationStyle = CitationStyle.NUMBERED):
        self.default_style = default_style
        self._source_registry: Dict[str, SourceMetadata] = {}
        self._citation_counter = 0

    def register_source(self, source: SourceMetadata) -> int:
        """Register a source and return its citation index."""
        self._citation_counter += 1
        self._source_registry[source.url] = source
        return self._citation_counter

    def get_source(self, url: str) -> Optional[SourceMetadata]:
        """Get source by URL."""
        return self._source_registry.get(url)

    def get_all_sources(self) -> List[SourceMetadata]:
        """Get all registered sources."""
        return list(self._source_registry.values())

    def generate_citations(
        self,
        sources: List[SourceMetadata],
        style: Optional[CitationStyle] = None,
    ) -> List[Citation]:
        """Generate citations for a list of sources."""
        style = style or self.default_style
        citations = []

        for i, source in enumerate(sources, 1):
            # Register if not already
            if source.url not in self._source_registry:
                self._citation_counter += 1
                self._source_registry[source.url] = source

            citation = self._format_citation(source, i, style)
            citations.append(citation)

        return citations

    def _format_citation(self, source: SourceMetadata, index: int, style: CitationStyle) -> Citation:
        """Format citation according to style."""
        if style == CitationStyle.NUMBERED:
            return self._format_numbered(source, index)
        elif style == CitationStyle.APA:
            return self._format_apa(source, index)
        elif style == CitationStyle.MLA:
            return self._format_mla(source, index)
        elif style == CitationStyle.CHICAGO:
            return self._format_chicago(source, index)
        elif style == CitationStyle.IEEE:
            return self._format_ieee(source, index)
        elif style == CitationStyle.HARVARD:
            return self._format_harvard(source, index)
        elif style == CitationStyle.SIMPLE:
            return self._format_simple(source, index)
        else:
            return self._format_numbered(source, index)

    def _format_numbered(self, source: SourceMetadata, index: int) -> Citation:
        """Numbered citation style [1]."""
        title = source.title or "Untitled"
        domain = source.domain or "Unknown source"
        year = ""
        if source.published_date:
            try:
                dt = datetime.fromisoformat(source.published_date.replace("Z", "+00:00"))
                year = f" ({dt.year})"
            except Exception:
                pass

        formatted = f"[{index}] {title}{year}. {domain}. URL: {source.url}"
        in_text = f"[{index}]"

        return Citation(
            index=index,
            source=source,
            style=CitationStyle.NUMBERED,
            formatted=formatted,
            in_text=in_text,
        )

    def _format_apa(self, source: SourceMetadata, index: int) -> Citation:
        """APA citation style."""
        author = source.author or source.domain or "Unknown Author"
        year = "n.d."
        if source.published_date:
            try:
                dt = datetime.fromisoformat(source.published_date.replace("Z", "+00:00"))
                year = str(dt.year)
            except Exception:
                pass

        title = source.title or "Untitled"
        domain = source.domain or ""

        formatted = f"{author} ({year}). {title}. {domain}. {source.url}"
        in_text = f"({author}, {year})"

        return Citation(
            index=index,
            source=source,
            style=CitationStyle.APA,
            formatted=formatted,
            in_text=in_text,
        )

    def _format_mla(self, source: SourceMetadata, index: int) -> Citation:
        """MLA citation style."""
        author = source.author or source.domain or "Unknown Author"
        title = source.title or "Untitled"
        domain = source.domain or "Unknown Source"

        if source.published_date:
            try:
                dt = datetime.fromisoformat(source.published_date.replace("Z", "+00:00"))
                pub_date = dt.strftime("%d %b. %Y")
            except Exception:
                pub_date = "n.d."
        else:
            pub_date = "n.d."

        formatted = f'{author}. "{title}." {domain}, {pub_date}, {source.url}.'
        in_text = f"({author.split()[0] if author else 'Source'})"

        return Citation(
            index=index,
            source=source,
            style=CitationStyle.MLA,
            formatted=formatted,
            in_text=in_text,
        )

    def _format_chicago(self, source: SourceMetadata, index: int) -> Citation:
        """Chicago citation style."""
        author = source.author or source.domain or "Unknown Author"
        title = source.title or "Untitled"
        domain = source.domain or "Unknown Source"

        if source.published_date:
            try:
                dt = datetime.fromisoformat(source.published_date.replace("Z", "+00:00"))
                pub_date = dt.strftime("%B %d, %Y")
            except Exception:
                pub_date = "n.d."
        else:
            pub_date = "n.d."

        formatted = f"{author}. \"{title}.\" {domain}, {pub_date}. {source.url}."
        in_text = f"({author.split()[0] if author else 'Source'} {pub_date.split()[-1] if pub_date != 'n.d.' else ''})"

        return Citation(
            index=index,
            source=source,
            style=CitationStyle.CHICAGO,
            formatted=formatted,
            in_text=in_text,
        )

    def _format_ieee(self, source: SourceMetadata, index: int) -> Citation:
        """IEEE citation style."""
        title = source.title or "Untitled"
        domain = source.domain or "Unknown Source"

        if source.published_date:
            try:
                dt = datetime.fromisoformat(source.published_date.replace("Z", "+00:00"))
                year = dt.year
            except Exception:
                year = ""
        else:
            year = ""

        formatted = f"[{index}] {title}, {domain}{', ' + str(year) if year else ''}. [Online]. Available: {source.url}"
        in_text = f"[{index}]"

        return Citation(
            index=index,
            source=source,
            style=CitationStyle.IEEE,
            formatted=formatted,
            in_text=in_text,
        )

    def _format_harvard(self, source: SourceMetadata, index: int) -> Citation:
        """Harvard citation style."""
        author = source.author or source.domain or "Unknown Author"
        year = "n.d."
        if source.published_date:
            try:
                dt = datetime.fromisoformat(source.published_date.replace("Z", "+00:00"))
                year = str(dt.year)
            except Exception:
                pass

        title = source.title or "Untitled"
        domain = source.domain or ""

        formatted = f"{author} ({year}) '{title}', {domain}. Available at: {source.url} (Accessed: {datetime.now().strftime('%d %B %Y')})."
        in_text = f"({author}, {year})"

        return Citation(
            index=index,
            source=source,
            style=CitationStyle.HARVARD,
            formatted=formatted,
            in_text=in_text,
        )

    def _format_simple(self, source: SourceMetadata, index: int) -> Citation:
        """Simple citation style."""
        title = source.title or "Untitled"
        url = source.url

        formatted = f"{index}. {title} - {url}"
        in_text = f"({index})"

        return Citation(
            index=index,
            source=source,
            style=CitationStyle.SIMPLE,
            formatted=formatted,
            in_text=in_text,
        )

    def format_inline_citations(
        self,
        text: str,
        source_urls: List[str],
        style: Optional[CitationStyle] = None,
    ) -> str:
        """Add inline citations to text."""
        style = style or self.default_style

        # Ensure all sources are registered
        for url in source_urls:
            if url not in self._source_registry:
                # Create minimal source
                source = SourceMetadata(
                    url=url,
                    title="Source",
                    source_type=None,  # Would need to be set
                )
                self.register_source(source)

        # For now, append citations at end
        citations = self.generate_citations(
            [self._source_registry[url] for url in source_urls if url in self._source_registry],
            style=style,
        )

        citation_text = "\n\nReferences:\n" + "\n".join(c.formatted for c in citations)
        return text + citation_text

    def format_bibliography(
        self,
        style: Optional[CitationStyle] = None,
    ) -> List[Citation]:
        """Format full bibliography."""
        style = style or self.default_style
        sources = list(self._source_registry.values())
        return self.generate_citations(sources, style)

    def export_bibtex(self) -> str:
        """Export citations in BibTeX format."""
        entries = []
        for i, source in enumerate(self._source_registry.values(), 1):
            entry = self._to_bibtex(source, f"source{i}")
            entries.append(entry)
        return "\n\n".join(entries)

    def _to_bibtex(self, source: SourceMetadata, key: str) -> str:
        """Convert source to BibTeX entry."""
        entry_type = "@misc"
        fields = []

        if source.author:
            fields.append(f"  author = {{{source.author}}}")

        if source.title:
            fields.append(f"  title = {{{source.title}}}")

        if source.domain:
            fields.append(f"  howpublished = {{{source.domain}}}")

        if source.published_date:
            try:
                dt = datetime.fromisoformat(source.published_date.replace("Z", "+00:00"))
                fields.append(f"  year = {{{dt.year}}}")
                fields.append(f"  month = {{{dt.strftime('%b')}}}")
            except Exception:
                pass

        fields.append(f"  url = {{{source.url}}}")
        fields.append(f"  note = {{Accessed: {datetime.now().strftime('%Y-%m-%d')}}}")

        return f"{entry_type}{{{key},\n{',\n'.join(fields)}\n}}"

    def clear(self):
        """Clear all registered sources."""
        self._source_registry.clear()
        self._citation_counter = 0

    def get_source_count(self) -> int:
        """Get number of registered sources."""
        return len(self._source_registry)


class InlineCitationFormatter:
    """Format inline citations in text."""

    def __init__(self, citation_manager: CitationManager):
        self.citation_manager = citation_manager

    def add_citations_to_text(
        self,
        text: str,
        source_chunks: List[Dict[str, Any]],
        style: Optional[CitationStyle] = None,
    ) -> str:
        """Add inline citations to text based on source chunks."""
        style = style or CitationStyle.NUMBERED

        # Extract unique sources
        sources = []
        seen_urls = set()
        for chunk in source_chunks:
            url = chunk.get("source_url") or chunk.get("metadata", {}).get("source_url")
            if url and url not in seen_urls:
                seen_urls.add(url)
                source = chunk.get("source_metadata")
                if source:
                    sources.append(source)

        if not sources:
            return text

        # Generate citations
        citations = self.citation_manager.generate_citations(sources, style)

        # Map URLs to citation indices
        url_to_index = {}
        for i, source in enumerate(sources, 1):
            url_to_index[source.url] = i

        # Add inline citations
        # This is a simplified approach - in production, would use NLP to find
        # appropriate places to insert citations
        cited_text = text
        for chunk in source_chunks:
            url = chunk.get("source_url") or chunk.get("metadata", {}).get("source_url")
            if url in url_to_index:
                idx = url_to_index[url]
                in_text = f"[{idx}]" if style == CitationStyle.NUMBERED else f"(Source {idx})"
                # Simple approach: add citation at end of text
                # In production, would insert at relevant positions

        # For now, append references at end
        refs = "\n\nReferences:\n" + "\n".join(
            f"[{i}] {c.source.title or 'Untitled'} - {c.source.url}"
            for i, c in enumerate(
                self.citation_manager.generate_citations(
                    [s for s in self.citation_manager.get_all_sources()],
                    CitationStyle.NUMBERED,
                ),
                1
            )
        )

        return text + refs