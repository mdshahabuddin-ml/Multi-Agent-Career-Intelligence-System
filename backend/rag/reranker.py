from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum as PyEnum
from abc import ABC, abstractmethod
import logging
import asyncio

logger = logging.getLogger(__name__)


class RerankerType(str, PyEnum):
    """Types of rerankers."""
    CROSS_ENCODER = "cross_encoder"
    LLM = "llm"
    HYBRID = "hybrid"
    NONE = "none"


@dataclass
class RerankerConfig:
    """Configuration for reranking."""
    reranker_type: RerankerType = RerankerType.CROSS_ENCODER
    model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    top_k: int = 10
    batch_size: int = 32
    max_length: int = 512
    score_threshold: float = 0.0
    device: str = "auto"  # auto, cpu, cuda


@dataclass
class RerankResult:
    """Result of reranking."""
    chunk_id: str
    content: str
    original_score: float
    rerank_score: float
    metadata: Dict[str, Any]
    source_id: str
    source_title: str
    source_type: str
    source_url: str


class RerankerBase(ABC):
    """Abstract base class for rerankers."""

    def __init__(self, config: RerankerConfig):
        self.config = config

    @abstractmethod
    async def rerank(
        self,
        query: str,
        results: List[Dict[str, Any]],
    ) -> List[RerankResult]:
        """Rerank results for a query."""
        pass


class CrossEncoderReranker(RerankerBase):
    """Cross-encoder reranker using sentence-transformers."""

    def __init__(self, config: RerankerConfig):
        super().__init__(config)
        self._model = None
        self._device = None

    def _load_model(self):
        """Lazy load the cross-encoder model."""
        if self._model is None:
            try:
                from sentence_transformers import CrossEncoder
                import torch

                # Determine device
                if self.config.device == "auto":
                    self._device = "cuda" if torch.cuda.is_available() else "cpu"
                else:
                    self._device = self.config.device

                self._model = CrossEncoder(self.config.model_name, device=self._device)
                logger.info(f"Loaded cross-encoder: {self.config.model_name} on {self._device}")

            except ImportError:
                raise ImportError("sentence-transformers required for cross-encoder reranker")

    async def rerank(
        self,
        query: str,
        results: List[Dict[str, Any]],
    ) -> List[RerankResult]:
        """Rerank results using cross-encoder."""
        if not results:
            return []

        self._load_model()

        # Limit to top candidates
        candidates = results[:self.config.top_k * 3]

        # Prepare pairs for cross-encoder
        pairs = [(query, r.get("content", "")[:1000]) for r in candidates]

        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        scores = await loop.run_in_executor(
            None,
            self._model.predict,
            pairs,
            {"batch_size": self.config.batch_size, "show_progress_bar": False}
        )

        # Create reranked results
        reranked = []
        for i, (result, score) in enumerate(zip(candidates, scores)):
            if score >= self.config.score_threshold:
                reranked.append(RerankResult(
                    chunk_id=result.get("chunk_id", f"chunk_{i}"),
                    content=result.get("content", ""),
                    original_score=result.get("score", 0.0),
                    rerank_score=float(score),
                    metadata=result.get("metadata", {}),
                    source_id=result.get("source_id", ""),
                    source_title=result.get("source_title", ""),
                    source_type=result.get("source_type", ""),
                    source_url=result.get("source_url", ""),
                ))

        # Sort by rerank score descending
        reranked.sort(key=lambda x: x.rerank_score, reverse=True)

        return reranked[:self.config.top_k]


class LLMReranker(RerankerBase):
    """LLM-based reranker (uses LLM to judge relevance)."""

    def __init__(self, config: RerankerConfig, llm_client=None):
        super().__init__(config)
        self.llm_client = llm_client

    async def rerank(
        self,
        query: str,
        results: List[Dict[str, Any]],
    ) -> List[RerankResult]:
        """Rerank using LLM."""
        if not results or not self.llm_client:
            return [
                RerankResult(
                    chunk_id=r.get("chunk_id", f"chunk_{i}"),
                    content=r.get("content", ""),
                    original_score=r.get("score", 0.0),
                    rerank_score=r.get("score", 0.0),
                    metadata=r.get("metadata", {}),
                    source_id=r.get("source_id", ""),
                    source_title=r.get("source_title", ""),
                    source_type=r.get("source_type", ""),
                    source_url=r.get("source_url", ""),
                )
                for i, r in enumerate(results[:self.config.top_k])
            ]

        # Batch rerank with LLM
        candidates = results[:self.config.top_k * 3]

        # Create prompt for batch ranking
        prompt = self._create_rerank_prompt(query, candidates[:self.config.top_k])

        # Call LLM
        response = await self.llm_client.generate(prompt)

        # Parse response
        reranked = self._parse_rerank_response(response, results[:self.config.top_k])

        return reranked

    def _create_rerank_prompt(self, query: str, candidates: List[Dict]) -> str:
        """Create prompt for LLM reranking."""
        prompt = f"""You are an expert at evaluating search result relevance.
Query: {query}

Rate each result's relevance to the query on a scale of 0-10.

"""
        for i, candidate in enumerate(candidates):
            prompt += f"Result {i+1}:\n{candidate.get('content', '')[:500]}\n\n"

        prompt += "\nProvide scores as: Result 1: X, Result 2: Y, ..."
        return prompt

    def _parse_rerank_response(self, response: str, candidates: List[Dict]) -> List[RerankResult]:
        """Parse LLM rerank response."""
        # Simple parsing - in production would be more robust
        return [
            RerankResult(
                chunk_id=c.get("chunk_id", f"chunk_{i}"),
                content=c.get("content", ""),
                original_score=c.get("score", 0.0),
                rerank_score=c.get("score", 0.0),
                metadata=c.get("metadata", {}),
                source_id=c.get("source_id", ""),
                source_title=c.get("source_title", ""),
                source_type=c.get("source_type", ""),
                source_url=c.get("source_url", ""),
            )
            for i, c in enumerate(candidates[:10])
        ]


class HybridReranker:
    """Hybrid reranker combining multiple signals."""

    def __init__(
        self,
        cross_encoder: Optional["CrossEncoderReranker"] = None,
        llm_reranker: Optional["LLMReranker"] = None,
        vector_weight: float = 0.4,
        rerank_weight: float = 0.6,
    ):
        self.cross_encoder = cross_encoder
        self.llm_reranker = llm_reranker
        self.vector_weight = vector_weight
        self.rerank_weight = rerank_weight

    async def rerank(
        self,
        query: str,
        results: List[Dict[str, Any]],
    ) -> List[RerankResult]:
        """Rerank using hybrid approach."""
        if not results:
            return []

        # Get cross-encoder scores
        ce_results = []
        if self.cross_encoder:
            ce_results = await self.cross_encoder.rerank(query, results)

        # Get LLM scores if available
        llm_results = []
        if self.llm_reranker:
            llm_results = await self.llm_reranker.rerank(query, results)

        # Combine scores
        combined = self._combine_scores(results, ce_results, llm_results)

        return combined[:10]

    def _combine_scores(
        self,
        original: List[Dict],
        ce_results: List["RerankResult"],
        llm_results: List["RerankResult"],
    ) -> List[RerankResult]:
        """Combine multiple ranking signals."""
        # Create lookup maps
        ce_map = {r.chunk_id: r.rerank_score for r in ce_results}
        llm_map = {r.chunk_id: r.rerank_score for r in llm_results}

        combined = []
        for result in original:
            chunk_id = result.get("chunk_id", "")
            vector_score = result.get("score", 0.0)
            ce_score = ce_map.get(chunk_id, 0.0)
            llm_score = llm_map.get(chunk_id, 0.0)

            # Weighted combination
            final_score = (
                self.vector_weight * vector_score +
                self.rerank_weight * 0.5 * (ce_score + llm_score) / 2
            )

            combined.append(RerankResult(
                chunk_id=chunk_id,
                content=result.get("content", ""),
                original_score=vector_score,
                rerank_score=final_score,
                metadata=result.get("metadata", {}),
                source_id=result.get("source_id", ""),
                source_title=result.get("source_title", ""),
                source_type=result.get("source_type", ""),
                source_url=result.get("source_url", ""),
            ))

        # Sort by final score
        combined.sort(key=lambda x: x.rerank_score, reverse=True)
        return combined


class NoReranker(RerankerBase):
    """No-op reranker (pass-through)."""

    async def rerank(
        self,
        query: str,
        results: List[Dict[str, Any]],
    ) -> List[RerankResult]:
        """Pass through without reranking."""
        return [
            RerankResult(
                chunk_id=r.get("chunk_id", f"chunk_{i}"),
                content=r.get("content", ""),
                original_score=r.get("score", 0.0),
                rerank_score=r.get("score", 0.0),
                metadata=r.get("metadata", {}),
                source_id=r.get("source_id", ""),
                source_title=r.get("source_title", ""),
                source_type=r.get("source_type", ""),
                source_url=r.get("source_url", ""),
            )
            for i, r in enumerate(results[:10])
        ]


class RerankerFactory:
    """Factory for creating rerankers."""

    @staticmethod
    def create(reranker_type: str, config: "RerankerConfig", **kwargs) -> RerankerBase:
        """Create reranker by type."""
        if reranker_type == "cross_encoder":
            return CrossEncoderReranker(config)
        elif reranker_type == "llm":
            return LLMReranker(config, **kwargs)
        elif reranker_type == "hybrid":
            # Would need both cross_encoder and llm_reranker
            return CrossEncoderReranker(config)  # Fallback
        elif reranker_type == "none":
            return NoReranker(config)
        else:
            raise ValueError(f"Unknown reranker type: {reranker_type}")