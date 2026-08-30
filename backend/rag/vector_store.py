from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import logging
import json

from backend.rag.retriever import VectorStoreBase, RetrievalResult, RetrievalConfig

logger = logging.getLogger(__name__)


@dataclass
class QdrantConfig:
    """Configuration for Qdrant vector store."""
    host: str = "localhost"
    port: int = 6333
    api_key: Optional[str] = None
    collection_name: str = "careerintel"
    vector_size: int = 1536
    distance: str = "cosine"  # cosine, dot, euclidean
    timeout: float = 30.0
    prefer_grpc: bool = False
    https: bool = False


class QdrantVectorStore(VectorStoreBase):
    """Qdrant vector store implementation."""

    def __init__(self, config: QdrantConfig):
        self.config = config
        self._client = None
        self._collection_initialized = False

    def _get_client(self):
        """Get or create Qdrant client."""
        if self._client is None:
            try:
                from qdrant_client import QdrantClient
                self._client = QdrantClient(
                    host=self.config.host,
                    port=self.config.port,
                    api_key=self.config.api_key,
                    timeout=self.config.timeout,
                    prefer_grpc=self.config.prefer_grpc,
                    https=self.config.https,
                )
            except ImportError:
                raise ImportError("qdrant-client package required for Qdrant vector store")
        return self._client

    async def _ensure_collection(self):
        """Ensure collection exists."""
        if self._collection_initialized:
            return

        client = self._get_client()

        try:
            # Check if collection exists
            collections = client.get_collections().collections
            exists = any(c.name == self.config.collection_name for c in collections)

            if not exists:
                from qdrant_client.http import models
                client.create_collection(
                    collection_name=self.config.collection_name,
                    vectors_config=models.VectorParams(
                        size=self.config.vector_size,
                        distance=models.Distance(self.config.distance.upper()),
                    ),
                )
                logger.info(f"Created Qdrant collection: {self.config.collection_name}")

            self._collection_initialized = True

        except Exception as e:
            logger.error(f"Failed to initialize Qdrant collection: {e}")
            raise

    async def add_chunks(self, chunks: List["DocumentChunk"]) -> None:
        """Add document chunks to Qdrant."""
        await self._ensure_collection()

        client = self._get_client()

        from qdrant_client.http import models

        points = []
        for chunk in chunks:
            if chunk.embedding is None:
                logger.warning(f"Chunk {chunk.chunk_id} has no embedding, skipping")
                continue

            point = models.PointStruct(
                id=chunk.chunk_id,
                vector=chunk.embedding,
                payload={
                    "content": chunk.content,
                    "metadata": chunk.metadata,
                    "source_id": chunk.metadata.get("source_id", ""),
                    "source_title": chunk.metadata.get("source_title", ""),
                    "source_type": chunk.metadata.get("source_type", ""),
                    "source_url": chunk.metadata.get("source_url", ""),
                    "chunk_index": chunk.metadata.get("chunk_index", 0),
                },
            )
            points.append(point)

        if points:
            client.upsert(
                collection_name=self.config.collection_name,
                points=points,
                wait=True,
            )
            logger.info(f"Upserted {len(points)} chunks to Qdrant")

    async def search(
        self,
        query_embedding: List[float],
        top_k: int,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[RetrievalResult]:
        """Search for similar vectors in Qdrant."""
        await self._ensure_collection()

        client = self._get_client()

        from qdrant_client.http import models

        # Build filter
        query_filter = None
        if filters:
            filter_conditions = []
            for key, value in filters.items():
                if isinstance(value, list):
                    filter_conditions.append(
                        models.FieldCondition(key=key, match=models.MatchAny(any=value))
                    )
                else:
                    filter_conditions.append(
                        models.FieldCondition(key=key, match=models.MatchValue(value=value))
                    )
            if filter_conditions:
                query_filter = models.Filter(must=filter_conditions)

        # Search
        search_result = client.search(
            collection_name=self.config.collection_name,
            query_vector=query_embedding,
            limit=top_k,
            query_filter=query_filter,
            with_payload=True,
            with_vectors=False,
        )

        # Convert to RetrievalResult
        results = []
        for hit in search_result:
            payload = hit.payload or {}
            result = RetrievalResult(
                chunk_id=str(hit.id),
                content=payload.get("content", ""),
                score=hit.score,
                metadata=payload.get("metadata", {}),
                source_id=payload.get("source_id", ""),
                source_title=payload.get("source_title", ""),
                source_type=payload.get("source_type", ""),
                source_url=payload.get("source_url", ""),
            )
            results.append(result)

        return results

    async def delete_chunks(self, chunk_ids: List[str]) -> None:
        """Delete chunks by IDs."""
        await self._ensure_collection()

        client = self._get_client()
        from qdrant_client.http import models

        client.delete(
            collection_name=self.config.collection_name,
            points_selector=models.PointIdsList(points=chunk_ids),
            wait=True,
        )
        logger.info(f"Deleted {len(chunk_ids)} chunks from Qdrant")

    async def get_chunk(self, chunk_id: str) -> Optional["RetrievalResult"]:
        """Get a specific chunk by ID."""
        await self._ensure_collection()

        client = self._get_client()

        points = client.retrieve(
            collection_name=self.config.collection_name,
            ids=[chunk_id],
            with_payload=True,
            with_vectors=False,
        )

        if not points:
            return None

        hit = points[0]
        payload = hit.payload or {}

        return RetrievalResult(
            chunk_id=str(hit.id),
            content=payload.get("content", ""),
            score=1.0,
            metadata=payload.get("metadata", {}),
            source_id=payload.get("source_id", ""),
            source_title=payload.get("source_title", ""),
            source_type=payload.get("source_type", ""),
            source_url=payload.get("source_url", ""),
        )

    async def clear(self) -> None:
        """Clear all data by deleting and recreating collection."""
        client = self._get_client()
        try:
            client.delete_collection(self.config.collection_name)
            self._collection_initialized = False
            await self._ensure_collection()
            logger.info(f"Cleared Qdrant collection: {self.config.collection_name}")
        except Exception as e:
            logger.error(f"Failed to clear Qdrant collection: {e}")
            raise

    async def get_collection_info(self) -> Dict[str, Any]:
        """Get collection statistics."""
        await self._ensure_collection()

        client = self._get_client()
        info = client.get_collection(self.config.collection_name)

        return {
            "collection_name": self.config.collection_name,
            "vectors_count": info.vectors_count,
            "points_count": info.points_count,
            "status": info.status,
            "optimizer_status": info.optimizer_status,
        }


class InMemoryVectorStore(VectorStoreBase):
    """In-memory vector store for development/testing."""

    def __init__(self):
        self._chunks: Dict[str, Dict[str, Any]] = {}
        self._vectors: Dict[str, List[float]] = {}

    async def add_chunks(self, chunks: List["DocumentChunk"]) -> None:
        """Add chunks to in-memory store."""
        for chunk in chunks:
            if chunk.embedding is None:
                continue
            self._chunks[chunk.chunk_id] = {
                "content": chunk.content,
                "metadata": chunk.metadata,
                "source_id": chunk.metadata.get("source_id", ""),
                "source_title": chunk.metadata.get("source_title", ""),
                "source_type": chunk.metadata.get("source_type", ""),
                "source_url": chunk.metadata.get("source_url", ""),
            }
            self._vectors[chunk.chunk_id] = chunk.embedding

    async def search(
        self,
        query_embedding: List[float],
        top_k: int,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[RetrievalResult]:
        """Search using cosine similarity."""
        if not self._vectors:
            return []

        import numpy as np

        query_vec = np.array(query_embedding)
        query_norm = np.linalg.norm(query_vec)

        scores = []
        for chunk_id, vector in self._vectors.items():
            # Apply filters
            chunk_data = self._chunks.get(chunk_id, {})
            if filters:
                match = True
                for key, value in filters.items():
                    payload_value = chunk_data.get("metadata", {}).get(key)
                    if isinstance(value, list):
                        if payload_value not in value:
                            match = False
                            break
                    elif payload_value != value:
                        match = False
                        break
                if not match:
                    continue

            vec = np.array(vector)
            vec_norm = np.linalg.norm(vec)
            if query_norm > 0 and vec_norm > 0:
                similarity = np.dot(query_vec, vec) / (query_norm * vec_norm)
                scores.append((chunk_id, similarity))

        # Sort by score
        scores.sort(key=lambda x: x[1], reverse=True)

        # Return top k
        results = []
        for chunk_id, score in scores[:top_k]:
            chunk_data = self._chunks[chunk_id]
            results.append(RetrievalResult(
                chunk_id=chunk_id,
                content=chunk_data["content"],
                score=score,
                metadata=chunk_data.get("metadata", {}),
                source_id=chunk_data.get("source_id", ""),
                source_title=chunk_data.get("source_title", ""),
                source_type=chunk_data.get("source_type", ""),
                source_url=chunk_data.get("source_url", ""),
            ))

        return results

    async def delete_chunks(self, chunk_ids: List[str]) -> None:
        """Delete chunks by IDs."""
        for chunk_id in chunk_ids:
            self._chunks.pop(chunk_id, None)
            self._vectors.pop(chunk_id, None)

    async def get_chunk(self, chunk_id: str) -> Optional["RetrievalResult"]:
        """Get a specific chunk."""
        if chunk_id not in self._chunks:
            return None

        chunk_data = self._chunks[chunk_id]
        return RetrievalResult(
            chunk_id=chunk_id,
            content=chunk_data["content"],
            score=1.0,
            metadata=chunk_data.get("metadata", {}),
            source_id=chunk_data.get("source_id", ""),
            source_title=chunk_data.get("source_title", ""),
            source_type=chunk_data.get("source_type", ""),
            source_url=chunk_data.get("source_url", ""),
        )

    async def clear(self) -> None:
        """Clear all data."""
        self._chunks.clear()
        self._vectors.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get store statistics."""
        return {
            "total_chunks": len(self._chunks),
            "total_vectors": len(self._vectors),
        }


class VectorStoreFactory:
    """Factory for creating vector stores."""

    @staticmethod
    def create(store_type: str, config: Any) -> VectorStoreBase:
        """Create vector store by type."""
        if store_type == "qdrant":
            return QdrantVectorStore(config)
        elif store_type == "memory":
            return InMemoryVectorStore()
        else:
            raise ValueError(f"Unknown vector store type: {store_type}")

    @staticmethod
    def create_from_config(config: Dict[str, Any]) -> VectorStoreBase:
        """Create vector store from config dict."""
        store_type = config.get("type", "memory")

        if store_type == "qdrant":
            qdrant_config = QdrantConfig(
                host=config.get("host", "localhost"),
                port=config.get("port", 6333),
                api_key=config.get("api_key"),
                collection_name=config.get("collection_name", "careerintel"),
                vector_size=config.get("vector_size", 1536),
                distance=config.get("distance", "cosine"),
            )
            return QdrantVectorStore(qdrant_config)
        elif store_type == "memory":
            return InMemoryVectorStore()
        else:
            raise ValueError(f"Unknown vector store type: {store_type}")