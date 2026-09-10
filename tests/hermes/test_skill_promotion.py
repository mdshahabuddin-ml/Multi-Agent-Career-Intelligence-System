"""
Step 2 tests: safe skill promotion pipeline.

Flow under test:
    Improvement Suggestion → SkillCreator draft → quarantine
    → ApprovalManager → HUMAN APPROVAL → SkillRegistry → HermesSkill row

Every safety rule has a dedicated test. Uses real SkillCreator,
SkillRegistry and ApprovalManager (no mocks for the gate itself).
"""

from __future__ import annotations

import pytest

from backend.hermes.approval.manager import ApprovalManager
from backend.hermes_engine.skills.skill_creator import SkillCreator
from backend.hermes_engine.skills.skill_registry import SkillRegistry
from backend.hermes_engine.skills.skill_promotion import (
    ACTION_SKILL_PROMOTION,
    PromotionError,
    SkillPromotion,
)
from backend.models.hermes_skill import HermesSkill


async def _handler(**kwargs):
    return {"ok": True, "params": kwargs}


@pytest.fixture
def creator():
    creator = SkillCreator()
    creator.add_template("summarize", {
        "description": "Summarize text",
        "parameters": {"max_words": 100},
        "handler": _handler,
        "tags": ["nlp"],
    })
    return creator


@pytest.fixture
def promotion(creator):
    return SkillPromotion(
        creator=creator,
        registry=SkillRegistry(),
        approval=ApprovalManager(),
        db=None,
    )


def _suggestion(**overrides):
    base = {
        "agent_id": "agent-1",
        "category": "quality",
        "description": "Add a summarizer skill",
        "skill_name": "summarizer",
        "template": "summarize",
        "params": {"max_words": 50},
        "tags": ["auto"],
    }
    base.update(overrides)
    return base


class TestDraftCreation:
    def test_propose_creates_pending_draft(self, promotion):
        draft = promotion.propose_suggestion(_suggestion(), requester_id="user-7")
        assert draft.status == "pending"
        assert draft.skill_name == "summarizer"
        assert draft.approval_request_id is not None
        assert promotion.get_draft(draft.id) is draft

    def test_propose_does_not_register(self, promotion):
        registry = promotion._registry
        promotion.propose_suggestion(_suggestion(), requester_id="user-7")
        assert registry.has("summarizer") is False
        assert registry.list_all() == []

    def test_unknown_template_fails_fast_without_side_effects(self, promotion):
        with pytest.raises(PromotionError):
            promotion.propose_suggestion(_suggestion(template="nope"), requester_id="u")
        assert promotion.list_drafts() == []
        assert promotion._approval.get_pending() == []

    @pytest.mark.parametrize("bad", [
        {"description": ""}, {"description": "   "},
        {"skill_name": "not a name"}, {"skill_name": ""},
        {"skill_name": "9lives"}, {"template": ""},
        {"params": "not-a-dict"}, {"tags": "not-a-list"},
    ])
    def test_invalid_suggestions_rejected(self, promotion, bad):
        with pytest.raises(PromotionError):
            promotion.propose_suggestion(_suggestion(**bad), requester_id="u")
        assert promotion.list_drafts() == []

    def test_template_without_callable_handler_refused(self, promotion, creator):
        creator.add_template("broken", {"description": "no handler"})
        with pytest.raises(PromotionError, match="no callable handler"):
            promotion.propose_suggestion(_suggestion(template="broken"), requester_id="u")

    def test_duplicate_name_refused_at_propose_time(self, promotion):
        async def other(**kwargs):
            return None

        promotion._registry.register("summarizer", other)
        with pytest.raises(PromotionError, match="already registered"):
            promotion.propose_suggestion(_suggestion(), requester_id="u")


class TestNoExecutionBeforeApproval:
    def test_promotion_service_has_no_execute_path(self, promotion):
        assert not hasattr(promotion, "execute")
        draft = promotion.propose_suggestion(_suggestion(), requester_id="u")
        assert promotion._registry.get("summarizer") is None
        assert draft.status == "pending"

    def test_quarantined_draft_is_not_listed_as_skill(self, promotion):
        promotion.propose_suggestion(_suggestion(), requester_id="u")
        assert promotion._registry.list_all() == []
        assert promotion._registry.search("summar") == []


class TestApprovalPromotes:
    def test_approve_registers_and_reports(self, promotion):
        draft = promotion.propose_suggestion(_suggestion(), requester_id="user-7")
        result = promotion.approve(draft.approval_request_id, notes="looks good")
        assert result["skill_name"] == "summarizer"
        assert result["status"] == "approved"
        assert result["skill_row_id"] is None  # no db wired
        entry = promotion._registry.get("summarizer")
        assert entry is not None
        assert entry["description"] == "Add a summarizer skill"
        assert draft.status == "approved"

    def test_approve_persists_skill_row(self, creator, db_session):
        promotion = SkillPromotion(
            creator=creator, registry=SkillRegistry(),
            approval=ApprovalManager(), db=db_session)
        draft = promotion.propose_suggestion(_suggestion(), requester_id="user-7")
        result = promotion.approve(draft.approval_request_id)
        assert result["skill_row_id"] is not None
        row = db_session.query(HermesSkill).filter_by(name="summarizer").one()
        assert row.enabled is True
        assert row.description == "Add a summarizer skill"
        assert row.module_path is None  # template provenance, never imported

    def test_double_approve_refused(self, promotion):
        draft = promotion.propose_suggestion(_suggestion(), requester_id="u")
        promotion.approve(draft.approval_request_id)
        with pytest.raises(PromotionError):
            promotion.approve(draft.approval_request_id)

    def test_unknown_approval_refused(self, promotion):
        with pytest.raises(PromotionError):
            promotion.approve("does-not-exist")
        assert promotion._registry.list_all() == []


class TestRejectionPreventsPromotion:
    def test_reject_leaves_registry_and_table_empty(self, promotion):
        draft = promotion.propose_suggestion(_suggestion(), requester_id="u")
        rejected = promotion.reject(draft.approval_request_id, notes="not yet")
        assert rejected.status == "rejected"
        assert promotion._registry.has("summarizer") is False
        assert promotion._registry.list_all() == []

    def test_reject_persists_nothing(self, creator, db_session):
        promotion = SkillPromotion(
            creator=creator, registry=SkillRegistry(),
            approval=ApprovalManager(), db=db_session)
        draft = promotion.propose_suggestion(_suggestion(), requester_id="u")
        promotion.reject(draft.approval_request_id)
        assert db_session.query(HermesSkill).filter_by(name="summarizer").count() == 0

    def test_rejected_draft_cannot_be_approved_later(self, promotion):
        draft = promotion.propose_suggestion(_suggestion(), requester_id="u")
        promotion.reject(draft.approval_request_id)
        with pytest.raises(PromotionError):
            promotion.approve(draft.approval_request_id)
        assert promotion._registry.has("summarizer") is False

    def test_second_reject_refused(self, promotion):
        draft = promotion.propose_suggestion(_suggestion(), requester_id="u")
        promotion.reject(draft.approval_request_id)
        with pytest.raises(PromotionError):
            promotion.reject(draft.approval_request_id)


class TestOwnerContext:
    def test_context_flows_to_draft_and_approval(self, promotion):
        draft = promotion.propose_suggestion(_suggestion(agent_id="agent-9"),
                                             requester_id="user-7")
        assert draft.agent_id == "agent-9"
        assert draft.requester_id == "user-7"
        pending = promotion._approval.get_pending()
        assert len(pending) == 1
        request = promotion._approval.get_request(draft.approval_request_id)
        assert request.action == ACTION_SKILL_PROMOTION
        assert request.requester_id == "user-7"
        assert request.data["agent_id"] == "agent-9"
        assert request.data["draft_id"] == draft.id
        assert request.data["skill_name"] == "summarizer"
