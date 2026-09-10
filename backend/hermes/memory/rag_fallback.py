"""
RAG fallback for Hermes memory retrieval: use existing RAG when needed.

Rule: local agent memories win. The existing RAG retriever
(``RetrieverBase.retrieve``) is consulted ONLY when local results are
thin (fewer than ``min_results``) AND a retriever was supplied. RAG hits
are marked ``source: "rag"`` and de-duplicated against local content.

Degradation contract: RAG failures (missing embeddings, no vector store,
network errors, unexpected payloads) NEVER propagate — the caller gets
local results. ``rag_retriever=None`` means local-only. Local-retrieval
errors are real errors and still propagate.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Awaitable, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


def _rag_hit_to_memory(hit: Any, agent_id: str, category: Optional[str]) -> Dict[str, Any]:
    """Convert one RAG RetrievalResult (or mapping) to a memory-shaped dict."""
    try:
        payload = hit.to_dict() if hasattr(hit, "to_dict") else dict(hit)
    except Exception:  # noqa: BLE001 - defensive, payload shapes vary
        payload = {"text": str(hit)}
    if not isinstance(payload, dict):
        payload = {"text": str(payload)}
    content = (
        payload.get("text")
        or payload.get("content")
        or payload.get("chunk")
        or json.dumps(payload, default=str)[:2000]
    )
    metadata = {
        key: payload[key]
        for key in ("score", "source", "document_id", "chunk_id", "metadata")
        if key in payload and key != "source"
    }
    metadata["rag_source"] = payload.get("source", "rag")
    return {
        "id": f"rag:{payload.get('chunk_id') or payload.get('document_id') or id(hit)}",
        "agent_id": agent_id,
        "content": content,
        "category": category or "rag",
        "metadata": metadata,
        "source": "rag",
    }


async def retrieve_with_fallback(
    local_retrieve: Callable[..., Awaitable[List[Dict[str, Any]]]],
    agent_id: str,
    query: str,
    limit: int = 10,
    category: Optional[str] = None,
    rag_retriever: Any = None,
    min_results: int = 1,
) -> List[Dict[str, Any]]:
    """Retrieve local memories, topping up from RAG only when needed."""
    local = await local_retrieve(agent_id=agent_id, query=query, limit=limit, category=category)
    local = list(local or [])
    if len(local) >= max(1, limit) or len(local) >= max(1, min_results) or rag_retriever is None:
        return local[: max(1, limit)]
    try:
        hits = await rag_retriever.retrieve(query)
    except Exception as exc:  # noqa: BLE001 - RAG is best-effort by contract
        logger.info("RAG fallback unavailable, serving local memories: %s", exc)
        return local[: max(1, limit)]
    seen = set()
    for entry in local:
        try:
            seen.add(json.dumps(entry.get("content", ""), default=str))
        except Exception:  # noqa: BLE001 - defensive
            continue
    merged = list(local)
    for hit in hits or []:
        if len(merged) >= max(1, limit):
            break
        memory = _rag_hit_to_memory(hit, agent_id, category)
        try:
            fingerprint = json.dumps(memory["content"], default=str)
        except Exception:  # noqa: BLE001 - defensive
            fingerprint = str(memory["content"])
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        merged.append(memory)
    return merged[: max(1, limit)]
