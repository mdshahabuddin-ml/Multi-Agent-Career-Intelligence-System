from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass, field
from enum import Enum as PyEnum
from abc import ABC, abstractmethod
import logging
import asyncio

logger = logging.getLogger(__name__)


class EmbeddingProvider(str, PyEnum):
    """Supported embedding providers."""
    OPENAI = "openai"
    HUGGINGFACE = "huggingface"
    COHERE = "cohere"
    LOCAL = "local"
    MOCK = "mock"


@dataclass
class EmbeddingConfig:
    """Configuration for embedding model."""
    provider: EmbeddingProvider = EmbeddingProvider.OPENAI
    model_name: str = "text-embedding-3-small"
    dimensions: int = 1536
    batch_size: int = 100
    max_tokens: int = 8192
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    normalize: bool = True
    timeout: float = 30.0


@dataclass
class EmbeddingResult:
    """Result of embedding generation."""
    embeddings: List[List[float]]
    model: str
    usage: Dict[str, int] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class EmbeddingProviderBase(ABC):
    """Abstract base class for embedding providers."""

    def __init__(self, config: EmbeddingConfig):
        self.config = config
        self.model_name = config.model_name

    @abstractmethod
    async def embed_texts(self, texts: List[str]) -> EmbeddingResult:
        """Generate embeddings for multiple texts."""
        pass

    @abstractmethod
    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        pass

    def _normalize(self, embeddings: List[List[float]]) -> List[List[float]]:
        """L2 normalize embeddings."""
        import math
        normalized = []
        for emb in embeddings:
            norm = math.sqrt(sum(x * x for x in emb))
            if norm > 0:
                normalized.append([x / norm for x in emb])
            else:
                normalized.append(emb)
        return normalized

    def _truncate_text(self, text: str) -> str:
        """Truncate text to max tokens."""
        # Rough approximation: 1 token ~= 4 chars
        max_chars = self.config.max_tokens * 4
        if len(text) > max_chars:
            return text[:max_chars]
        return text


class OpenAIEmbeddingProvider(EmbeddingProviderBase):
    """OpenAI embedding provider."""

    def __init__(self, config: EmbeddingConfig):
        super().__init__(config)
        try:
            import openai
            self.client = openai.AsyncOpenAI(
                api_key=config.api_key,
                base_url=config.base_url,
            )
        except ImportError:
            raise ImportError("openai package required for OpenAI embeddings")

    async def embed_texts(self, texts: List[str]) -> EmbeddingResult:
        texts = [self._truncate_text(t) for t in texts]

        # Process in batches
        all_embeddings = []
        total_tokens = 0

        for i in range(0, len(texts), self.config.batch_size):
            batch = texts[i:i + self.config.batch_size]
            response = await self.client.embeddings.create(
                model=self.model_name,
                input=batch,
                encoding_format="float",
            )
            batch_embeddings = [d.embedding for d in response.data]
            all_embeddings.extend(batch_embeddings)
            total_tokens += response.usage.total_tokens

        if self.config.normalize:
            all_embeddings = self._normalize(all_embeddings)

        return EmbeddingResult(
            embeddings=all_embeddings,
            model=self.model_name,
            usage={"total_tokens": total_tokens},
        )

    async def embed_text(self, text: str) -> List[float]:
        result = await self.embed_texts([text])
        return result.embeddings[0]


class HuggingFaceEmbeddingProvider(EmbeddingProviderBase):
    """HuggingFace embedding provider (local or API)."""

    def __init__(self, config: EmbeddingConfig):
        super().__init__(config)
        self._model = None
        self._tokenizer = None
        self._device = "cuda" if self._is_cuda_available() else "cpu"

    def _is_cuda_available(self) -> bool:
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False

    def _load_model(self):
        """Lazy load model."""
        if self._model is None:
            try:
                from transformers import AutoModel, AutoTokenizer
                import torch

                self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
                self._model = AutoModel.from_pretrained(self.model_name).to(self._device)
                self._model.eval()
            except ImportError:
                raise ImportError("transformers and torch required for HuggingFace embeddings")

    async def embed_texts(self, texts: List[str]) -> EmbeddingResult:
        self._load_model()

        import torch

        texts = [self._truncate_text(t) for t in texts]
        all_embeddings = []

        for i in range(0, len(texts), self.config.batch_size):
            batch = texts[i:i + self.config.batch_size]

            # Tokenize
            inputs = self._tokenizer(
                batch,
                padding=True,
                truncation=True,
                max_length=self.config.max_tokens,
                return_tensors="pt",
            ).to(self._device)

            # Generate embeddings
            with torch.no_grad():
                outputs = self._model(**inputs)
                # Use CLS token or mean pooling
                embeddings = outputs.last_hidden_state[:, 0, :].cpu().numpy()

            all_embeddings.extend(embeddings.tolist())

        embeddings_list = [emb.tolist() for emb in all_embeddings]

        if self.config.normalize:
            embeddings_list = self._normalize(embeddings_list)

        return EmbeddingResult(
            embeddings=embeddings_list,
            model=self.model_name,
            usage={"total_tokens": sum(len(t.split()) for t in texts)},
        )

    async def embed_text(self, text: str) -> List[float]:
        result = await self.embed_texts([text])
        return result.embeddings[0]


class CohereEmbeddingProvider(EmbeddingProviderBase):
    """Cohere embedding provider."""

    def __init__(self, config: EmbeddingConfig):
        super().__init__(config)
        try:
            import cohere
            self.client = cohere.AsyncClient(api_key=config.api_key)
        except ImportError:
            raise ImportError("cohere package required for Cohere embeddings")

    async def embed_texts(self, texts: List[str]) -> EmbeddingResult:
        texts = [self._truncate_text(t) for t in texts]

        response = await self.client.embed(
            model=self.model_name,
            texts=texts,
            input_type="search_document",
        )

        embeddings = response.embeddings

        if self.config.normalize:
            embeddings = self._normalize(embeddings)

        return EmbeddingResult(
            embeddings=embeddings,
            model=self.model_name,
            usage={"total_tokens": sum(len(t.split()) for t in texts)},
        )

    async def embed_text(self, text: str) -> List[float]:
        result = await self.embed_texts([text])
        return result.embeddings[0]


class MockEmbeddingProvider(EmbeddingProviderBase):
    """Mock embedding provider for testing."""

    def __init__(self, config: EmbeddingConfig):
        super().__init__(config)
        self.dimensions = config.dimensions

    async def embed_texts(self, texts: List[str]) -> EmbeddingResult:
        import random
        import hashlib

        embeddings = []
        for text in texts:
            # Deterministic embeddings based on text hash
            seed = int(hashlib.md5(text.encode()).hexdigest()[:8], 16)
            random.seed(seed)
            emb = [random.uniform(-1, 1) for _ in range(self.dimensions)]
            embeddings.append(emb)

        if self.config.normalize:
            embeddings = self._normalize(embeddings)

        return EmbeddingResult(
            embeddings=embeddings,
            model=self.model_name,
            usage={"total_tokens": sum(len(t.split()) for t in texts)},
        )

    async def embed_text(self, text: str) -> List[float]:
        result = await self.embed_texts([text])
        return result.embeddings[0]


class EmbeddingManager:
    """Manage embedding providers and operations."""

    def __init__(self, config: Optional[EmbeddingConfig] = None):
        self.config = config or EmbeddingConfig()
        self._provider: Optional[EmbeddingProviderBase] = None
        self._cache: Dict[str, List[float]] = {}

    def _get_provider(self) -> EmbeddingProviderBase:
        """Get or create embedding provider."""
        if self._provider is None:
            self._provider = self._create_provider()
        return self._provider

    def _create_provider(self) -> EmbeddingProviderBase:
        """Create provider based on config."""
        if self.config.provider == EmbeddingProvider.OPENAI:
            return OpenAIEmbeddingProvider(self.config)
        elif self.config.provider == EmbeddingProvider.HUGGINGFACE:
            return HuggingFaceEmbeddingProvider(self.config)
        elif self.config.provider == EmbeddingProvider.COHERE:
            return CohereEmbeddingProvider(self.config)
        elif self.config.provider == EmbeddingProvider.MOCK:
            return MockEmbeddingProvider(self.config)
        else:
            raise ValueError(f"Unknown provider: {self.config.provider}")

    async def embed_texts(self, texts: List[str]) -> EmbeddingResult:
        """Generate embeddings for multiple texts."""
        provider = self._get_provider()
        return await provider.embed_texts(texts)

    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding for single text."""
        provider = self._get_provider()
        return await provider.embed_text(text)

    async def embed_chunks(self, chunks: List["DocumentChunk"]) -> List["DocumentChunk"]:
        """Embed document chunks."""
        texts = [chunk.content for chunk in chunks]
        result = await self.embed_texts(texts)

        for chunk, embedding in zip(chunks, result.embeddings):
            chunk.embedding = embedding

        return chunks

    async def embed_query(self, query: str) -> List[float]:
        """Embed a search query (may use different prompt template)."""
        provider = self._get_provider()
        return await provider.embed_text(query)

    def set_provider(self, provider: EmbeddingProviderBase):
        """Set custom provider."""
        self._provider = provider

    def clear_cache(self):
        """Clear embedding cache."""
        self._cache.clear()