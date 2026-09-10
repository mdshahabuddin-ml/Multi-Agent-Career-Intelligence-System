"""
Canonical state-transition tables for the project's existing lifecycles.

Every edge below was derived from observed writer code — NOT invented:

- ContentStatus edges mirror ``ContentScheduler`` (assign_slot,
  request_retry, schedule_from_run), ``PublishingService`` (_apply_success /
  _apply_failure) and the ``content_calendar`` publish gate.
- PipelineStage edges mirror ``CareerContentService`` (forward runner
  DRAFT→…→PENDING_REVIEW, ``_decide``, ``_require_state`` + re-verify
  outcomes). ``REVIEW_REQUIRED`` aliases ``PENDING_REVIEW`` (same value).
- ApprovalStatus edges mirror ``hermes/approval/manager.py``
  (approve/reject on PENDING; EXPIRED declared by the model).
- Agent lifecycle values mirror the documented set in
  ``backend/agents/registry.py`` (``AgentStatus.status``: idle/busy/error/
  offline — free-form str, so the table pins the contract).

Keys and members are plain value strings, so tables work with enum
members, raw DB strings, and API payloads alike. Terminal states map to
an empty set. ``cancelled`` has no observed inbound writer; it is terminal
and documented as such rather than given invented edges.
"""

from __future__ import annotations

from typing import Dict, FrozenSet

# ----------------------------------------------------------------------
# ContentCalendar lifecycle (ContentStatus values)
# ----------------------------------------------------------------------
CONTENT_STATUS_TRANSITIONS: Dict[str, FrozenSet[str]] = {
    "draft": frozenset({"scheduled"}),
    "pending": frozenset({"scheduled"}),
    "scheduled": frozenset({"scheduled", "published", "failed"}),
    "retry": frozenset({"scheduled", "published", "failed"}),
    "failed": frozenset({"retry", "scheduled"}),
    "published": frozenset(),
    "cancelled": frozenset(),  # terminal; no inbound writer observed
}

# ----------------------------------------------------------------------
# Content pipeline lifecycle (PipelineStage values)
# ----------------------------------------------------------------------
PIPELINE_STAGE_TRANSITIONS: Dict[str, FrozenSet[str]] = {
    "draft": frozenset({"intake"}),
    "intake": frozenset({"topic_selection", "failed"}),
    "topic_selection": frozenset({"research", "failed"}),
    "research": frozenset({"generation", "failed"}),
    "generation": frozenset({"verification", "failed"}),
    "verification": frozenset({"formatting", "failed"}),
    "formatting": frozenset({"pending_review"}),
    "pending_review": frozenset({"approved", "rejected", "pending_review", "failed"}),
    "approved": frozenset(),  # terminal; approved runs are final
    "rejected": frozenset({"pending_review", "failed"}),
    "failed": frozenset({"pending_review", "failed"}),
}

# ----------------------------------------------------------------------
# Human approval lifecycle (ApprovalStatus values)
# ----------------------------------------------------------------------
APPROVAL_STATUS_TRANSITIONS: Dict[str, FrozenSet[str]] = {
    "pending": frozenset({"approved", "rejected", "expired"}),
    "approved": frozenset(),
    "rejected": frozenset(),
    "expired": frozenset(),
}

# ----------------------------------------------------------------------
# Agent lifecycle (AgentStatus.status documented values)
# ----------------------------------------------------------------------
AGENT_LIFECYCLE_TRANSITIONS: Dict[str, FrozenSet[str]] = {
    "idle": frozenset({"busy", "offline"}),
    "busy": frozenset({"idle", "error", "offline"}),
    "error": frozenset({"idle", "offline"}),
    "offline": frozenset({"idle"}),
}

MACHINES: Dict[str, Dict[str, FrozenSet[str]]] = {
    "content": CONTENT_STATUS_TRANSITIONS,
    "pipeline": PIPELINE_STAGE_TRANSITIONS,
    "approval": APPROVAL_STATUS_TRANSITIONS,
    "agent": AGENT_LIFECYCLE_TRANSITIONS,
}


def _value(state: object) -> str:
    """Normalize an enum member or raw string to its value string."""
    value = getattr(state, "value", state)
    return str(value) if not isinstance(value, str) else value


def is_allowed(machine: str, current: object, target: object) -> bool:
    """True when ``current → target`` is a legal edge of ``machine``."""
    try:
        table = MACHINES[machine]
    except KeyError:
        raise KeyError(f"Unknown state machine: {machine!r}") from None
    return _value(target) in table.get(_value(current), frozenset())


def allowed_next(machine: str, current: object) -> FrozenSet[str]:
    """Legal successor states for ``current`` (empty when terminal/unknown)."""
    try:
        table = MACHINES[machine]
    except KeyError:
        raise KeyError(f"Unknown state machine: {machine!r}") from None
    return table.get(_value(current), frozenset())


def is_terminal(machine: str, current: object) -> bool:
    """True when ``current`` is a known state with no outbound edges."""
    try:
        table = MACHINES[machine]
    except KeyError:
        raise KeyError(f"Unknown state machine: {machine!r}") from None
    key = _value(current)
    return key in table and not table[key]
