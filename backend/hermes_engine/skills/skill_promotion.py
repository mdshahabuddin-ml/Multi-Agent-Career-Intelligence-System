"""
Safe skill promotion pipeline (Step 2).

Required flow:
    Improvement Suggestion
      → SkillCreator draft (template-based ONLY, inert data)
      → Draft quarantine (in-memory, never executable)
      → ApprovalManager
      → HUMAN APPROVAL
      → SkillRegistry registration
      → HermesSkill persistence

Safety properties (load-bearing, each covered by tests):
1. A suggestion NEVER directly registers a skill (``propose`` has no
   registry-write path; registration happens only in ``approve``).
2. ``SkillCreator`` output stays inert data until a human approves.
3. No source code is written anywhere (no file IO in this module).
4. No module is imported (``SkillLoader`` is never touched here).
5. This module exposes NO execute path; quarantined drafts are not in the
   registry, so no executor can reach them.
6. Every promotion goes through ``ApprovalManager``; unknown, decided, or
   expired requests cannot promote.
7./8. Rejection (or any promotion failure) leaves the registry AND the
   ``hermes_skills`` table untouched — rejected skills are not executable.
9. Templates are human-registered callables: drafts resolve their handler
   ONLY from templates already present in ``SkillCreator``. There is no
   function-based path (a suggestion dict cannot smuggle a callable in —
   only template NAME + params are read; anything else is ignored).
"""

from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

_SKILL_NAME_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")

ACTION_SKILL_PROMOTION = "skill_promotion"


@dataclass
class SkillDraft:
    """A quarantined promotion proposal. Inert until approved."""

    id: str
    skill_name: str
    template_name: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    agent_id: str = ""
    requester_id: str = ""
    user_id: Optional[int] = None
    suggestion: Dict[str, Any] = field(default_factory=dict)
    approval_request_id: Optional[str] = None
    status: str = "pending"  # pending | approved | rejected | failed
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    decided_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "skill_name": self.skill_name,
            "template_name": self.template_name,
            "description": self.description,
            "parameters": dict(self.parameters),
            "tags": list(self.tags),
            "agent_id": self.agent_id,
            "requester_id": self.requester_id,
            "user_id": self.user_id,
            "approval_request_id": self.approval_request_id,
            "status": self.status,
            "created_at": self.created_at,
            "decided_at": self.decided_at,
        }


class PromotionError(ValueError):
    """Promotion rejected by validation, approval state, or registration."""


class SkillPromotion:
    """Human-gated promotion of improvement suggestions into skills.

    Reuses ``SkillCreator`` (drafts), ``ApprovalManager`` (human gate),
    ``SkillRegistry`` (activation) and the ``HermesSkill`` model
    (persistence). Pass ``db=None`` for registry-only operation.
    """

    def __init__(
        self,
        creator: Any = None,
        registry: Any = None,
        approval: Any = None,
        db: Any = None,
    ):
        from backend.hermes.approval.manager import ApprovalManager
        from backend.hermes_engine.skills.skill_creator import SkillCreator
        from backend.hermes_engine.skills.skill_registry import SkillRegistry

        self._creator = creator or SkillCreator()
        self._registry = registry or SkillRegistry()
        self._approval = approval or ApprovalManager()
        self._db = db
        self._drafts: Dict[str, SkillDraft] = {}

    # ------------------------------------------------------------------
    # Step 1: suggestion → quarantined draft + approval request (no writes
    # to registry or skill table happen here — structurally impossible:
    # this method never references them for writing).
    # ------------------------------------------------------------------
    def propose_suggestion(
        self,
        suggestion: Dict[str, Any],
        requester_id: str,
        timeout_seconds: int = 300,
        user_id: Optional[int] = None,
    ) -> SkillDraft:
        """Validate a suggestion, build an inert draft, request approval.

        ``user_id`` (when known) is recorded as the skill owner for restart
        rehydration; ``None`` preserves the legacy ownerless row.
        """
        if not isinstance(suggestion, dict):
            raise PromotionError("Suggestion must be a mapping")
        description = str(suggestion.get("description") or "").strip()
        if not description:
            raise PromotionError("Suggestion needs a non-empty description")
        skill_name = str(suggestion.get("skill_name") or "").strip()
        if _SKILL_NAME_RE.fullmatch(skill_name) is None:
            raise PromotionError(
                f"Invalid skill_name: {skill_name!r} (public identifier required)")
        template_name = str(suggestion.get("template") or "").strip()
        if not template_name:
            raise PromotionError("Suggestion must name an existing skill template")
        params = suggestion.get("params") or {}
        if not isinstance(params, dict):
            raise PromotionError("Suggestion params must be a mapping")
        tags = suggestion.get("tags") or []
        if not isinstance(tags, list) or any(not isinstance(t, str) for t in tags):
            raise PromotionError("Suggestion tags must be a list of strings")
        if self._registry.has(skill_name):
            raise PromotionError(f"Skill '{skill_name}' is already registered")

        # Template must already exist (human-registered). Unknown template →
        # fail fast here; nothing is quarantined, nothing is requested.
        try:
            spec = self._creator.create_from_template(
                template_name, skill_name,
                params={"description": description, **params},
            )
        except ValueError as exc:
            raise PromotionError(f"Cannot draft skill: {exc}") from exc
        handler = spec.get("handler")
        if not callable(handler):
            raise PromotionError(
                f"Template '{template_name}' provides no callable handler; "
                "promotion requires human-registered code")

        draft = SkillDraft(
            id=str(uuid.uuid4()),
            skill_name=skill_name,
            template_name=template_name,
            description=description,
            parameters=dict(spec.get("parameters") or {}),
            tags=list(spec.get("tags") or []) + list(tags),
            agent_id=str(suggestion.get("agent_id") or ""),
            requester_id=requester_id,
            user_id=user_id,
            suggestion={k: v for k, v in suggestion.items() if k != "handler"},
        )
        approval_request = self._approval.request_approval(
            action=ACTION_SKILL_PROMOTION,
            description=f"Promote skill '{skill_name}' from approved suggestion: {description}",
            requester_id=requester_id,
            data={
                "draft_id": draft.id,
                "skill_name": skill_name,
                "template": template_name,
                "agent_id": draft.agent_id,
            },
            timeout_seconds=timeout_seconds,
        )
        draft.approval_request_id = approval_request.id
        self._drafts[draft.id] = draft
        logger.info("Skill draft %s quarantined pending approval %s",
                    draft.id, approval_request.id)
        return draft

    # ------------------------------------------------------------------
    # Step 2: HUMAN APPROVAL → register → persist. Every other outcome
    # leaves registry and table untouched.
    # ------------------------------------------------------------------
    def approve(self, approval_request_id: str, notes: str = "") -> Dict[str, Any]:
        """Approve a promotion: register the skill, persist it, return info."""
        draft = self._draft_for_request(approval_request_id)
        decided = self._approval.approve(approval_request_id, notes=notes)
        if decided is None:
            raise PromotionError(
                f"Approval request {approval_request_id!r} is not pending; promotion refused")
        try:
            return self._activate(draft, approved=True)
        except Exception:
            draft.status = "failed"
            draft.decided_at = datetime.utcnow().isoformat()
            raise

    def reject(self, approval_request_id: str, notes: str = "") -> SkillDraft:
        """Reject a promotion: registry and table stay untouched."""
        draft = self._draft_for_request(approval_request_id)
        decided = self._approval.reject(approval_request_id, notes=notes)
        if decided is None:
            raise PromotionError(
                f"Approval request {approval_request_id!r} is not pending; nothing to reject")
        draft.status = "rejected"
        draft.decided_at = datetime.utcnow().isoformat()
        logger.info("Skill draft %s rejected; not promotable", draft.id)
        return draft

    # ------------------------------------------------------------------
    # Inspection (read-only; never mutates promotion state)
    # ------------------------------------------------------------------
    def get_draft(self, draft_id: str) -> Optional[SkillDraft]:
        return self._drafts.get(draft_id)

    def list_drafts(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        return [d.to_dict() for d in self._drafts.values()
                if status is None or d.status == status]

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _draft_for_request(self, approval_request_id: str) -> SkillDraft:
        for draft in self._drafts.values():
            if draft.approval_request_id == approval_request_id:
                if draft.status != "pending":
                    raise PromotionError(
                        f"Draft {draft.id} is already {draft.status}; promotion refused")
                return draft
        raise PromotionError(
            f"No quarantined draft for approval request {approval_request_id!r}")

    def _activate(self, draft: SkillDraft, approved: bool) -> Dict[str, Any]:
        """Register + persist an approved draft. No execute path exists here."""
        _ = approved
        # Re-resolve the handler from the human-registered template at
        # activation time (never trust a stored callable blindly, never
        # import anything: templates are live human code by construction).
        spec = self._creator.create_from_template(
            draft.template_name, draft.skill_name, params=draft.parameters)
        handler: Optional[Callable] = spec.get("handler")
        if not callable(handler):
            raise PromotionError(
                f"Template '{draft.template_name}' no longer provides a callable handler")
        self._registry.register(
            draft.skill_name,
            handler,
            description=draft.description,
            parameters=draft.parameters,
            tags=draft.tags,
        )
        skill_row_id: Optional[int] = None
        if self._db is not None:
            skill_row_id = self._persist_skill_row(draft)
        draft.status = "approved"
        draft.decided_at = datetime.utcnow().isoformat()
        logger.info("Skill '%s' promoted (draft %s)", draft.skill_name, draft.id)
        return {
            "skill_name": draft.skill_name,
            "draft_id": draft.id,
            "approval_request_id": draft.approval_request_id,
            "skill_row_id": skill_row_id,
            "status": draft.status,
        }

    def _persist_skill_row(self, draft: SkillDraft) -> int:
        """Persist to the EXISTING hermes_skills table (no new tables)."""
        from backend.models.hermes_skill import HermesSkill

        row = HermesSkill(
            name=draft.skill_name,
            description=draft.description,
            module_path=None,
            function_name=None,
            parameters_json=dict(draft.parameters),
            tags_json=list(draft.tags),
            enabled=True,
            user_id=draft.user_id,
            template=draft.template_name,
        )
        self._db.add(row)
        try:
            self._db.commit()
        except Exception:
            self._db.rollback()
            # Registry write already happened: roll it back too so a
            # half-promoted skill can never exist.
            try:
                self._registry.unregister(draft.skill_name)
            except Exception:  # noqa: BLE001 - best effort rollback
                pass
            raise PromotionError(
                f"Skill '{draft.skill_name}' could not be persisted; promotion aborted")
        self._db.refresh(row)
        return row.id
