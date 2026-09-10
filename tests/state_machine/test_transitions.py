"""
Tests for central transition tables.

Tables must cover every member of the real enums — if an enum gains a
member, these tests fail until the table documents its edges. That is
intentional: undocumented states are a bug source.
"""

from __future__ import annotations

import pytest

from backend.hermes.approval.manager import ApprovalStatus
from backend.models.content_calendar import ContentStatus
from backend.models.content_pipeline_run import PipelineStage
from backend.state_machine import transitions as T


def _members(enum_cls):
    seen = set()
    for member in enum_cls:
        if member.value not in seen:  # skip aliases (e.g. REVIEW_REQUIRED)
            seen.add(member.value)
            yield member


class TestTableCoverage:
    def test_content_table_covers_enum(self):
        assert {m.value for m in _members(ContentStatus)} == set(T.CONTENT_STATUS_TRANSITIONS)

    def test_pipeline_table_covers_enum(self):
        assert {m.value for m in _members(PipelineStage)} == set(T.PIPELINE_STAGE_TRANSITIONS)

    def test_approval_table_covers_enum(self):
        assert {m.value for m in _members(ApprovalStatus)} == set(T.APPROVAL_STATUS_TRANSITIONS)

    def test_agent_table_covers_documented_values(self):
        assert set(T.AGENT_LIFECYCLE_TRANSITIONS) == {"idle", "busy", "error", "offline"}


class TestContentEdges:
    @pytest.mark.parametrize("source,target", [
        ("draft", "scheduled"), ("pending", "scheduled"),
        ("scheduled", "scheduled"), ("scheduled", "published"), ("scheduled", "failed"),
        ("retry", "scheduled"), ("retry", "published"), ("retry", "failed"),
        ("failed", "retry"), ("failed", "scheduled"),
    ])
    def test_legal_edges(self, source, target):
        assert T.is_allowed("content", source, target) is True
        assert target in T.allowed_next("content", source)

    @pytest.mark.parametrize("source,target", [
        ("draft", "published"), ("draft", "failed"), ("draft", "retry"),
        ("pending", "published"), ("pending", "failed"),
        ("published", "scheduled"), ("published", "failed"), ("published", "retry"),
        ("failed", "published"), ("failed", "draft"),
        ("cancelled", "scheduled"),
    ])
    def test_illegal_edges(self, source, target):
        assert T.is_allowed("content", source, target) is False

    def test_terminal_states(self):
        assert T.is_terminal("content", "published") is True
        assert T.is_terminal("content", "cancelled") is True
        assert T.is_terminal("content", "scheduled") is False

    def test_enum_members_accepted(self):
        assert T.is_allowed("content", ContentStatus.DRAFT, ContentStatus.SCHEDULED)
        assert not T.is_allowed("content", ContentStatus.DRAFT, ContentStatus.PUBLISHED)


class TestPipelineEdges:
    @pytest.mark.parametrize("source,target", [
        ("draft", "intake"), ("intake", "topic_selection"),
        ("topic_selection", "research"), ("research", "generation"),
        ("generation", "verification"), ("verification", "formatting"),
        ("formatting", "pending_review"),
        ("pending_review", "approved"), ("pending_review", "rejected"),
        ("pending_review", "pending_review"), ("pending_review", "failed"),
        ("rejected", "pending_review"), ("rejected", "failed"),
        ("failed", "pending_review"), ("failed", "failed"),
        ("intake", "failed"), ("verification", "failed"),
    ])
    def test_legal_edges(self, source, target):
        assert T.is_allowed("pipeline", source, target) is True

    @pytest.mark.parametrize("source,target", [
        ("draft", "approved"), ("approved", "rejected"), ("approved", "pending_review"),
        ("approved", "failed"), ("rejected", "approved"), ("failed", "approved"),
        ("research", "approved"), ("pending_review", "research"),
    ])
    def test_illegal_edges(self, source, target):
        assert T.is_allowed("pipeline", source, target) is False

    def test_approved_is_terminal(self):
        assert T.is_terminal("pipeline", "approved") is True
        assert T.allowed_next("pipeline", "approved") == frozenset()

    def test_review_required_alias_normalizes(self):
        # REVIEW_REQUIRED shares PENDING_REVIEW's value — no duplicate row needed.
        assert PipelineStage.REVIEW_REQUIRED.value == "pending_review"
        assert T.is_allowed("pipeline", PipelineStage.REVIEW_REQUIRED, "approved")


class TestApprovalAndAgentEdges:
    @pytest.mark.parametrize("target", ["approved", "rejected", "expired"])
    def test_pending_fanout(self, target):
        assert T.is_allowed("approval", "pending", target)

    @pytest.mark.parametrize("source", ["approved", "rejected", "expired"])
    def test_approval_terminals(self, source):
        assert T.is_terminal("approval", source) is True

    def test_approval_enum_members(self):
        assert T.is_allowed("approval", ApprovalStatus.PENDING, ApprovalStatus.APPROVED)
        assert not T.is_allowed("approval", ApprovalStatus.APPROVED, ApprovalStatus.PENDING)

    @pytest.mark.parametrize("source,target", [
        ("idle", "busy"), ("idle", "offline"),
        ("busy", "idle"), ("busy", "error"), ("busy", "offline"),
        ("error", "idle"), ("error", "offline"), ("offline", "idle"),
    ])
    def test_agent_legal(self, source, target):
        assert T.is_allowed("agent", source, target) is True

    @pytest.mark.parametrize("source,target", [
        ("idle", "error"), ("error", "busy"), ("offline", "busy"), ("offline", "error"),
    ])
    def test_agent_illegal(self, source, target):
        assert T.is_allowed("agent", source, target) is False


class TestUnknowns:
    def test_unknown_machine_raises(self):
        with pytest.raises(KeyError):
            T.is_allowed("nope", "a", "b")
        with pytest.raises(KeyError):
            T.allowed_next("nope", "a")

    def test_unknown_state_is_closed(self):
        assert T.is_allowed("content", "nonexistent", "scheduled") is False
        assert T.allowed_next("content", "nonexistent") == frozenset()
        assert T.is_terminal("content", "nonexistent") is False
