from typing import List, Dict, Any, Optional, Iterator
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import logging
import hashlib
import mimetypes

from backend.research_engine.state.research_context import SourceMetadata, ResearchSourceType

logger = logging.getLogger(__name__)


@dataclass
class DocumentChunk:
    """A chunk of document content."""
    content: str
    metadata: Dict[str, Any]
    chunk_id: str = field(default_factory=lambda: hashlib.md5(str(datetime.utcnow().timestamp()).encode()).hexdigest()[:12])
    embedding: Optional[List[float]] = None
    token_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "content": self.content,
            "metadata": self.metadata,
            "token_count": self.token_count,
        }


@dataclass
class LoadedDocument:
    """A loaded document with chunks."""
    source_id: str
    source_metadata: SourceMetadata
    chunks: List[DocumentChunk]
    full_content: str
    loaded_at: datetime = field(default_factory=datetime.utcnow)


class BaseLoader:
    """Base class for document loaders."""

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        min_chunk_size: int = 100,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size

    def load(self, source: SourceMetadata) -> LoadedDocument:
        """Load a document from source."""
        content = self._extract_content(source)
        chunks = self._chunk_content(content, source)
        return LoadedDocument(
            source_id=source.url,
            source_metadata=source,
            chunks=chunks,
            full_content=content,
        )

    def load_batch(self, sources: List[SourceMetadata]) -> List[LoadedDocument]:
        """Load multiple documents."""
        return [self.load(source) for source in sources]

    def _extract_content(self, source: SourceMetadata) -> str:
        """Extract text content from source. Override in subclasses."""
        return source.custom_metadata.get("content", source.custom_metadata.get("snippet", ""))

    def _chunk_content(self, content: str, source: SourceMetadata) -> List[DocumentChunk]:
        """Split content into overlapping chunks."""
        if not content:
            return []

        chunks = []
        start = 0
        content_len = len(content)

        while start < content_len:
            end = min(start + self.chunk_size, content_len)

            # Try to break at sentence boundary
            if end < content_len:
                # Look for sentence ending within overlap zone
                search_start = max(start + self.chunk_size - self.chunk_overlap, start)
                sentence_end = content.rfind(". ", search_start, end)
                if sentence_end != -1 and sentence_end > start:
                    end = sentence_end + 1

            chunk_text = content[start:end].strip()

            if len(chunk_text) >= self.min_chunk_size:
                chunk = DocumentChunk(
                    content=chunk_text,
                    metadata={
                        "source_id": source.url,
                        "source_title": source.title,
                        "source_type": source.source_type.value,
                        "source_domain": source.domain,
                        "chunk_index": len(chunks),
                        "start_char": start,
                        "end_char": end,
                    },
                    token_count=len(chunk_text.split()),
                )
                chunks.append(chunk)

            # Move start forward with overlap
            start = end - self.chunk_overlap if end < content_len else content_len

            if start >= content_len:
                break

        return chunks


class ResumeLoader(BaseLoader):
    """Load and chunk resume documents."""

    def __init__(self, **kwargs):
        super().__init__(chunk_size=800, chunk_overlap=100, **kwargs)

    def _extract_content(self, source: SourceMetadata) -> str:
        content = source.custom_metadata.get("content", source.custom_metadata.get("snippet", ""))

        # Add structured resume data if available
        parsed = source.custom_metadata.get("parsed_data", {})
        if parsed:
            sections = []
            for section_name, section_content in parsed.items():
                if section_content:
                    sections.append(f"=== {section_name.upper()} ===\n{section_content}")
            if sections:
                content = "\n\n".join(sections) + "\n\n" + content

        return content

    def _chunk_content(self, content: str, source: SourceMetadata) -> List[DocumentChunk]:
        # For resumes, try to keep sections together
        chunks = []
        sections = content.split("\n\n===")

        for section in sections:
            if not section.strip():
                continue

            section_chunks = super()._chunk_content(section.strip(), source)
            for chunk in section_chunks:
                chunk.metadata["resume_section"] = section.split("\n")[0].replace("===", "").strip().lower()
                chunks.append(chunk)

        return chunks


class JobLoader(BaseLoader):
    """Load and chunk job postings."""

    def __init__(self, **kwargs):
        super().__init__(chunk_size=1000, chunk_overlap=150, **kwargs)

    def _extract_content(self, source: SourceMetadata) -> str:
        content = source.custom_metadata.get("content", source.custom_metadata.get("snippet", ""))

        # Add structured job data
        structured = source.custom_metadata.get("structured_data", {})
        if structured:
            parts = []
            if structured.get("title"):
                parts.append(f"Title: {structured['title']}")
            if structured.get("company"):
                parts.append(f"Company: {structured['company']}")
            if structured.get("location"):
                parts.append(f"Location: {structured['location']}")
            if structured.get("description"):
                parts.append(f"Description: {structured['description']}")
            if structured.get("requirements"):
                parts.append(f"Requirements: {structured['requirements']}")
            if structured.get("skills"):
                parts.append(f"Skills: {', '.join(structured['skills'])}")
            if parts:
                content = "\n".join(parts) + "\n\n" + content

        return content


class NewsLoader(BaseLoader):
    """Load and chunk news articles."""

    def __init__(self, **kwargs):
        super().__init__(chunk_size=1200, chunk_overlap=200, **kwargs)

    def _extract_content(self, source: SourceMetadata) -> str:
        content = source.custom_metadata.get("content", source.custom_metadata.get("snippet", ""))

        # Add news metadata
        if source.author:
            content = f"Author: {source.author}\n{content}"
        if source.published_date:
            content = f"Published: {source.published_date}\n{content}"

        return content


class CompanyLoader(BaseLoader):
    """Load and chunk company profiles."""

    def __init__(self, **kwargs):
        super().__init__(chunk_size=1000, chunk_overlap=150, **kwargs)

    def _extract_content(self, source: SourceMetadata) -> str:
        content = source.custom_metadata.get("content", source.custom_metadata.get("snippet", ""))

        # Add structured company data
        structured = source.custom_metadata.get("structured_data", {})
        if structured:
            parts = []
            if structured.get("name"):
                parts.append(f"Company: {structured['name']}")
            if structured.get("industry"):
                parts.append(f"Industry: {structured['industry']}")
            if structured.get("size"):
                parts.append(f"Size: {structured['size']}")
            if structured.get("location"):
                parts.append(f"Location: {structured['location']}")
            if structured.get("tech_stack"):
                parts.append(f"Tech Stack: {', '.join(structured['tech_stack'])}")
            if structured.get("benefits"):
                parts.append(f"Benefits: {', '.join(structured['benefits'])}")
            if structured.get("culture"):
                parts.append(f"Culture: {structured['culture']}")
            if parts:
                content = "\n".join(parts) + "\n\n" + content

        return content


class ResearchLoader(BaseLoader):
    """Load and chunk research reports."""

    def __init__(self, **kwargs):
        super().__init__(chunk_size=1500, chunk_overlap=300, **kwargs)

    def _extract_content(self, source: SourceMetadata) -> str:
        content = source.custom_metadata.get("content", source.custom_metadata.get("snippet", ""))

        # Add research metadata
        research = source.custom_metadata.get("research_data", {})
        if research:
            parts = []
            if research.get("query"):
                parts.append(f"Research Query: {research['query']}")
            if research.get("executive_summary"):
                parts.append(f"Executive Summary: {research['executive_summary']}")
            if research.get("key_findings"):
                parts.append(f"Key Findings: {'; '.join(research['key_findings'])}")
            if research.get("recommendations"):
                parts.append(f"Recommendations: {'; '.join(research['recommendations'])}")
            if parts:
                content = "\n".join(parts) + "\n\n" + content

        return content


class DocumentLoaderFactory:
    """Factory for creating appropriate loaders."""

    _loaders = {
        ResearchSourceType.WEB: BaseLoader,
        ResearchSourceType.NEWS: NewsLoader,
        ResearchSourceType.ACADEMIC: BaseLoader,
        ResearchSourceType.COMPANY: CompanyLoader,
        ResearchSourceType.JOB_BOARD: JobLoader,
        ResearchSourceType.SOCIAL: BaseLoader,
        ResearchSourceType.GOVERNMENT: BaseLoader,
        ResearchSourceType.INTERNAL: BaseLoader,
        ResearchSourceType.OTHER: BaseLoader,
    }

    _special_loaders = {
        "resume": ResumeLoader,
        "job": JobLoader,
        "news": NewsLoader,
        "company": CompanyLoader,
        "research": ResearchLoader,
    }

    @classmethod
    def get_loader(
        cls,
        source_type: ResearchSourceType,
        document_type: Optional[str] = None,
        **kwargs
    ) -> BaseLoader:
        """Get appropriate loader for source type."""
        if document_type and document_type in cls._special_loaders:
            return cls._special_loaders[document_type](**kwargs)

        loader_class = cls._loaders.get(source_type, BaseLoader)
        return loader_class(**kwargs)

    @classmethod
    def register_loader(cls, source_type: ResearchSourceType, loader_class: type):
        """Register a custom loader."""
        cls._loaders[source_type] = loader_class

    @classmethod
    def register_special_loader(cls, document_type: str, loader_class: type):
        """Register a special document type loader."""
        cls._special_loaders[document_type] = loader_class