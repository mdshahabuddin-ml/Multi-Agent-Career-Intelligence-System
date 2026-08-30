from typing import List, Dict, Any, Optional, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum as PyEnum
from abc import ABC, abstractmethod
import logging
import math
import numpy as np

from backend.rag.embeddings import EmbeddingManager, EmbeddingConfig, EmbeddingProvider

logger = logging.getLogger(__name__)


class SearchMode(str, PyEnum):
    """Search modes for retrieval."""
    VECTOR = "vector"  # Pure vector similarity
    KEYWORD = "keyword"  # Pure keyword/BM25
    HYBRID = "hybrid"  # Combined vector + keyword
    SEMANTIC = "semantic"  # Vector with semantic query expansion


@dataclass
class RetrievalConfig:
    """Configuration for retrieval."""
    mode: SearchMode = SearchMode.HYBRID
    top_k: int = 10
    vector_weight: float = 0.7
    keyword_weight: float = 0.3
    similarity_threshold: float = 0.0
    rerank: bool = False
    rerank_top_k: int = 50
    filters: Dict[str, Any] = field(default_factory=dict)
    include_metadata: bool = True


@dataclass
class RetrievalResult:
    """A single retrieval result."""
    chunk_id: str
    content: str
    score: float
    metadata: Dict[str, Any]
    source_id: str
    source_title: str
    source_type: str
    source_url: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "content": self.content,
            "score": self.score,
            "metadata": self.metadata,
            "source_id": self.source_id,
            "source_title": self.source_title,
            "source_type": self.source_type,
            "source_url": self.source_url,
        }


class VectorStoreBase(ABC):
    """Abstract base class for vector stores."""

    @abstractmethod
    async def add_chunks(self, chunks: List["DocumentChunk"]) -> None:
        """Add document chunks to the store."""
        pass

    @abstractmethod
    async def search(
        self,
        query_embedding: List[float],
        top_k: int,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[RetrievalResult]:
        """Search for similar chunks."""
        pass

    @abstractmethod
    async def delete_chunks(self, chunk_ids: List[str]) -> None:
        """Delete chunks by IDs."""
        pass

    @abstractmethod
    async def get_chunk(self, chunk_id: str) -> Optional[RetrievalResult]:
        """Get a specific chunk."""
        pass

    @abstractmethod
    async def clear(self) -> None:
        """Clear all data."""
        pass


class RetrieverBase(ABC):
    """Abstract base class for retrievers."""

    def __init__(self, embedding_manager: EmbeddingManager, config: RetrievalConfig):
        self.embedding_manager = embedding_manager
        self.config = config

    @abstractmethod
    async def retrieve(
        self,
        query: str,
        config: Optional[RetrievalConfig] = None,
    ) -> List[RetrievalResult]:
        """Retrieve relevant chunks for a query."""
        pass


class HybridRetriever(RetrieverBase):
    """Hybrid retriever combining vector and keyword search."""

    def __init__(
        self,
        embedding_manager: EmbeddingManager,
        vector_store: VectorStoreBase,
        config: RetrievalConfig,
        keyword_index: Optional[Any] = None,
    ):
        super().__init__(embedding_manager, config)
        self.vector_store = vector_store
        self.keyword_index = keyword_index

    async def retrieve(
        self,
        query: str,
        config: Optional[RetrievalConfig] = None,
    ) -> List[RetrievalResult]:
        """Retrieve relevant chunks using hybrid search."""
        cfg = config or self.config

        if cfg.mode == SearchMode.VECTOR:
            return await self._vector_search(query, cfg)
        elif cfg.mode == SearchMode.KEYWORD:
            return await self._keyword_search(query, cfg)
        elif cfg.mode == SearchMode.HYBRID:
            return await self._hybrid_search(query, cfg)
        elif cfg.mode == SearchMode.SEMANTIC:
            return await self._semantic_search(query, cfg)
        else:
            return await self._hybrid_search(query, cfg)

    async def _vector_search(
        self,
        query: str,
        config: RetrievalConfig,
    ) -> List[RetrievalResult]:
        """Pure vector similarity search."""
        query_embedding = await self.embedding_manager.embed_query(query)
        results = await self.vector_store.search(
            query_embedding=query_embedding,
            top_k=config.top_k,
            filters=config.filters,
        )

        # Filter by threshold
        if config.similarity_threshold > 0:
            results = [r for r in results if r.score >= config.similarity_threshold]

        return results[:config.top_k]

    async def _keyword_search(
        self,
        query: str,
        config: RetrievalConfig,
    ) -> List[RetrievalResult]:
        """Keyword-based search (BM25 or similar)."""
        if not self.keyword_index:
            logger.warning("No keyword index available, falling back to vector search")
            return await self._vector_search(query, config)

        # Use keyword index
        # This would integrate with Elasticsearch, OpenSearch, or similar
        # For now, return empty
        return []

    async def _hybrid_search(
        self,
        query: str,
        config: RetrievalConfig,
    ) -> List[RetrievalResult]:
        """Combined vector and keyword search."""
        # Get vector results
        vector_results = await self._vector_search(query, config)

        # Get keyword results if available
        keyword_results = []
        if self.keyword_index:
            keyword_results = await self._keyword_search(query, config)

        # Combine results using reciprocal rank fusion (RRF)
        combined = self._reciprocal_rank_fusion(
            vector_results,
            keyword_results,
            config.vector_weight,
            config.keyword_weight,
        )

        return combined[:config.top_k]

    async def _semantic_search(
        self,
        query: str,
        config: RetrievalConfig,
    ) -> List[RetrievalResult]:
        """Semantic search with query expansion."""
        # Expand query with related terms
        expanded_queries = await self._expand_query(query)

        all_results = []
        for q in expanded_queries:
            results = await self._vector_search(q, config)
            all_results.extend(results)

        # Deduplicate and re-rank
        seen = set()
        unique_results = []
        for r in all_results:
            if r.chunk_id not in seen:
                seen.add(r.chunk_id)
                unique_results.append(r)

        return unique_results[:config.top_k]

    def _reciprocal_rank_fusion(
        self,
        vector_results: List[RetrievalResult],
        keyword_results: List[RetrievalResult],
        vector_weight: float,
        keyword_weight: float,
        k: int = 60,
    ) -> List[RetrievalResult]:
        """Combine results using Reciprocal Rank Fusion."""
        scores = {}

        # Score vector results
        for rank, result in enumerate(vector_results):
            rrf_score = vector_weight * (1.0 / (k + rank + 1))
            if result.chunk_id in scores:
                scores[result.chunk_id]["score"] += rrf_score
            else:
                scores[result.chunk_id] = {
                    "result": result,
                    "score": rrf_score,
                }

        # Score keyword results
        for rank, result in enumerate(keyword_results):
            rrf_score = keyword_weight * (1.0 / (k + rank + 1))
            if result.chunk_id in scores:
                scores[result.chunk_id]["score"] += rrf_score
            else:
                scores[result.chunk_id] = {
                    "result": result,
                    "score": rrf_score,
                }

        # Sort by combined score
        sorted_results = sorted(
            scores.values(),
            key=lambda x: x["score"],
            reverse=True,
        )

        return [item["result"] for item in sorted_results]

    async def _expand_query(self, query: str) -> List[str]:
        """Expand query with related terms."""
        # In production, this would use an LLM or knowledge graph
        # For now, return original query
        return [query]


class BM25Retriever:
    """BM25 keyword retriever using rank_bm25 or similar."""

    def __init__(self, chunks: List["DocumentChunk"]):
        self.chunks = chunks
        self._corpus = None
        self._bm25 = None
        self._build_index()

    def _build_index(self):
        """Build BM25 index."""
        try:
            from rank_bm25 import BM25Okapi
        except ImportError:
            logger.warning("rank_bm25 not installed, BM25 search unavailable")
            return

        # Tokenize corpus
        tokenized_corpus = []
        for chunk in self.chunks:
            tokens = chunk.content.lower().split()
            tokenized_corpus.append(tokens)

        self._corpus = tokenized_corpus
        self._bm25 = BM25Okapi(tokenized_corpus)

    def search(self, query: str, top_k: int = 10) -> List[Tuple[int, float]]:
        """Search using BM25."""
        if not self._bm25:
            return []

        tokenized_query = query.lower().split()
        scores = self._bm25.get_scores(tokenized_query)

        # Get top k indices
        top_indices = np.argsort(scores)[::-1][:top_k]

        results = []
        for idx in top_indices:
            if scores[idx] > 0:
                results.append((idx, scores[idx]))

        return results


import numpy as np