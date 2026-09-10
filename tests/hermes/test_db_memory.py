"""
Tests for DB-backed Hermes memory: HermesConversation/HermesMemory models
-> Memory Manager -> existing DB -> RAG-when-needed fallback.

The pre-existing file backend (MemoryStorage) and in-memory service are
untouched; a dedicated test asserts the live file path still works.
"""

from __future__ import annotations

import pytest

from backend.hermes.memory import MemoryManager, MemoryStorage
from backend.hermes.memory.conversation_store import DbConversationStore
from backend.hermes.memory.db_storage import DbMemoryStorage
from backend.hermes.memory.rag_fallback import retrieve_with_fallback


@pytest.fixture
def db_store(db_session, test_user):
    return DbMemoryStorage(db_session, test_user.id)


@pytest.fixture
def conv_store(db_session, test_user):
    return DbConversationStore(db_session, test_user.id)


class TestDbMemoryStorage:
    @pytest.mark.asyncio
    async def test_store_and_get_roundtrip(self, db_store):
        memory_id = await db_store.store(agent_id="a1", content="hello db", category="notes")
        assert isinstance(memory_id, str)
        entry = await db_store.get(memory_id)
        assert entry["content"] == "hello db"
        assert entry["category"] == "notes"
        assert entry["agent_id"] == "a1"

    @pytest.mark.asyncio
    async def test_non_string_content_roundtrips(self, db_store):
        payload = {"plan": ["x", "y"], "n": 3}
        memory_id = await db_store.store(agent_id="a1", content=payload)
        assert (await db_store.get(memory_id))["content"] == payload

    @pytest.mark.asyncio
    async def test_get_missing_and_garbage(self, db_store):
        assert await db_store.get("999999") is None
        assert await db_store.get("not-an-id") is None
        assert await db_store.get("") is None

    @pytest.mark.asyncio
    async def test_user_isolation(self, db_store, db_session, second_user):
        from backend.hermes.memory.db_storage import DbMemoryStorage as S

        other = S(db_session, second_user.id)
        memory_id = await db_store.store(agent_id="a1", content="mine")
        assert await other.get(memory_id) is None
        assert await other.delete(memory_id) is False
        assert await db_store.get(memory_id) is not None

    @pytest.mark.asyncio
    async def test_delete(self, db_store):
        memory_id = await db_store.store(agent_id="a1", content="bye")
        assert await db_store.delete(memory_id) is True
        assert await db_store.get(memory_id) is None
        assert await db_store.delete(memory_id) is False
        assert await db_store.delete("garbage") is False

    @pytest.mark.asyncio
    async def test_recent_order_limit_category(self, db_store):
        for i in range(5):
            await db_store.store(agent_id="a1", content=f"m{i}", category="odd" if i % 2 else "even")
        recent = await db_store.get_recent(agent_id="a1", limit=2)
        assert [r["content"] for r in recent] == ["m4", "m3"]
        evens = await db_store.get_recent(agent_id="a1", limit=10, category="even")
        assert {r["content"] for r in evens} == {"m0", "m2", "m4"}
        assert await db_store.get_recent(agent_id="nobody") == []

    @pytest.mark.asyncio
    async def test_search(self, db_store):
        await db_store.store(agent_id="a1", content="Python async patterns", category="tech")
        await db_store.store(agent_id="a1", content="Grocery list", category="life")
        hits = await db_store.search(agent_id="a1", query="async")
        assert len(hits) == 1 and hits[0]["category"] == "tech"
        assert await db_store.search(agent_id="a1", query="") == []
        assert await db_store.search(agent_id="a1", query="async", category="life") == []

    @pytest.mark.asyncio
    async def test_clear_agent_isolation(self, db_store):
        await db_store.store(agent_id="a1", content="x")
        await db_store.store(agent_id="a1", content="y")
        await db_store.store(agent_id="a2", content="z")
        assert await db_store.clear_agent(agent_id="a1") == 2
        assert await db_store.clear_agent(agent_id="a1") == 0
        assert len(await db_store.get_recent(agent_id="a2")) == 1

    def test_stats(self, db_session, test_user):
        import asyncio

        async def _run():
            store = DbMemoryStorage(db_session, test_user.id)
            await store.store(agent_id="a1", content="x", category="c1")
            await store.store(agent_id="a1", content="y", category="c1")
            await store.store(agent_id="a1", content="z", category="c2")
            return store.get_stats(agent_id="a1")

        stats = asyncio.run(_run())
        assert stats["total"] == 3
        assert stats["categories"] == {"c1": 2, "c2": 1}

    def test_interface_parity_with_file_backend(self):
        file_methods = {m for m in dir(MemoryStorage) if not m.startswith("_")}
        db_methods = {m for m in dir(DbMemoryStorage) if not m.startswith("_")}
        assert file_methods <= db_methods

    @pytest.mark.asyncio
    async def test_works_through_memory_manager(self, db_session, test_user):
        manager = MemoryManager(storage=DbMemoryStorage(db_session, test_user.id))
        memory_id = await manager.store(agent_id="a1", content="via manager", category="t")
        assert memory_id
        assert await manager.delete(memory_id) is True


class TestDbConversationStore:
    @pytest.mark.asyncio
    async def test_append_history_order(self, conv_store):
        await conv_store.append("c1", "a1", "user", "Hello")
        await conv_store.append("c1", "a1", "assistant", "Hi there")
        history = await conv_store.history("c1", "a1")
        assert [t["role"] for t in history] == ["user", "assistant"]
        assert history[0]["content"] == "Hello"
        assert history[0]["conversation_id"] == "c1"

    @pytest.mark.asyncio
    async def test_history_limit_and_isolation(self, conv_store):
        for i in range(4):
            await conv_store.append("c1", "a1", "user", f"m{i}")
        await conv_store.append("c1", "a2", "user", "other-agent")
        await conv_store.append("c2", "a1", "user", "other-conv")
        history = await conv_store.history("c1", "a1", limit=2)
        assert [t["content"] for t in history] == ["m0", "m1"]
        assert await conv_store.history("missing", "a1") == []

    @pytest.mark.asyncio
    async def test_validation(self, conv_store):
        with pytest.raises(ValueError):
            await conv_store.append("c1", "a1", "alien", "hi")
        with pytest.raises(ValueError):
            await conv_store.append("c1", "a1", "user", "   ")
        with pytest.raises(ValueError):
            await conv_store.append("", "a1", "user", "hi")

    @pytest.mark.asyncio
    async def test_clear(self, conv_store):
        await conv_store.append("c1", "a1", "user", "a")
        await conv_store.append("c1", "a1", "user", "b")
        await conv_store.append("c2", "a1", "user", "c")
        assert await conv_store.clear("c1", "a1") == 2
        assert await conv_store.history("c1", "a1") == []
        assert len(await conv_store.history("c2", "a1")) == 1

    @pytest.mark.asyncio
    async def test_user_isolation(self, conv_store, db_session, second_user):
        await conv_store.append("c1", "a1", "user", "secret")
        other = DbConversationStore(db_session, second_user.id)
        assert await other.history("c1", "a1") == []
        assert await other.clear("c1", "a1") == 0


class _StubHit:
    def __init__(self, text, score=0.9):
        self._payload = {"text": text, "score": score, "chunk_id": text[:8]}

    def to_dict(self):
        return dict(self._payload)


class _StubRag:
    def __init__(self, hits=None, error=None):
        self.hits = hits or []
        self.error = error
        self.calls = 0

    async def retrieve(self, query):
        self.calls += 1
        if self.error:
            raise self.error
        return list(self.hits)


async def _local(entries):
    async def _retrieve(agent_id="", query="", limit=10, category=None):
        return list(entries[:limit])

    return _retrieve


class TestRagFallback:
    @pytest.mark.asyncio
    async def test_local_sufficient_skips_rag(self):
        rag = _StubRag(hits=[_StubHit("from rag")])
        local = await _local([{"id": "1", "content": "a"}, {"id": "2", "content": "b"}])
        out = await retrieve_with_fallback(local, "a1", "q", limit=2, rag_retriever=rag)
        assert len(out) == 2 and rag.calls == 0
        assert all("source" not in entry for entry in out)

    @pytest.mark.asyncio
    async def test_thin_local_tops_up_from_rag(self):
        rag = _StubRag(hits=[_StubHit("rag one"), _StubHit("rag two")])
        local = await _local([{"id": "1", "content": "local one"}])
        out = await retrieve_with_fallback(local, "a1", "q", limit=3, rag_retriever=rag,
                                           min_results=2)
        assert len(out) == 3
        assert out[0]["content"] == "local one"
        assert out[1]["source"] == "rag" and out[1]["content"] == "rag one"

    @pytest.mark.asyncio
    async def test_default_fires_rag_only_when_local_empty(self):
        rag = _StubRag(hits=[_StubHit("rag one")])
        local = await _local([{"id": "1", "content": "local one"}])
        out = await retrieve_with_fallback(local, "a1", "q", limit=3, rag_retriever=rag)
        assert [e["content"] for e in out] == ["local one"] and rag.calls == 0
        empty = await _local([])
        out = await retrieve_with_fallback(empty, "a1", "q", limit=2, rag_retriever=rag)
        assert [e["content"] for e in out] == ["rag one"] and rag.calls == 1

    @pytest.mark.asyncio
    async def test_rag_failure_serves_local(self):
        rag = _StubRag(error=RuntimeError("vector store down"))
        local = await _local([{"id": "1", "content": "local"}])
        out = await retrieve_with_fallback(local, "a1", "q", limit=5, rag_retriever=rag)
        assert [e["content"] for e in out] == ["local"]

    @pytest.mark.asyncio
    async def test_no_retriever_is_local_only(self):
        local = await _local([{"id": "1", "content": "local"}])
        out = await retrieve_with_fallback(local, "a1", "q", limit=5, rag_retriever=None)
        assert [e["content"] for e in out] == ["local"]

    @pytest.mark.asyncio
    async def test_dedupe_and_cap(self):
        rag = _StubRag(hits=[_StubHit("same"), _StubHit("new1"), _StubHit("new2")])
        local = await _local([{"id": "1", "content": "same"}])
        out = await retrieve_with_fallback(local, "a1", "q", limit=2, rag_retriever=rag,
                                           min_results=2)
        assert [e["content"] for e in out] == ["same", "new1"]

    @pytest.mark.asyncio
    async def test_local_errors_propagate(self):
        async def _bad(**kwargs):
            raise ValueError("db gone")

        with pytest.raises(ValueError):
            await retrieve_with_fallback(_bad, "a1", "q", rag_retriever=_StubRag())


class TestFileBackendUntouched:
    def test_file_storage_still_importable_and_shaped(self):
        assert hasattr(MemoryStorage, "store")
        assert "DbMemoryStorage" in dir(__import__("backend.hermes.memory", fromlist=["x"]))
