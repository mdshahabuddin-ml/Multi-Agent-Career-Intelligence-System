"""
Central guards: single enforcement point for lifecycle preconditions.

Each guard mirrors the EXACT legacy rule and message previously scattered
across ``ContentScheduler``, ``CareerContentService`` and the
``content_calendar`` publish gate, so delegating callers keep byte-identical
API behaviour (same 4xx codes, same detail strings).

``TransitionNotAllowed`` subclasses ``ValueError`` deliberately: existing
callers that catch ``ValueError``/``SchedulingError`` keep working without
modification.
"""

from __future__ import annotations

from typing import FrozenSet, Iterable, Optional

from backend.state_machine.transitions import _value, is_allowed


class TransitionNotAllowed(ValueError):
    """A lifecycle precondition failed. Carries machine + edge for logging."""

    def __init__(self, machine: str, current: str, target: str, reason: str):
        self.machine = machine
        self.current = current
        self.target = target
        super().__init__(reason)


def require_transition(machine: str, current: object, target: object,
                       action: str = "transition") -> str:
    """Enforce one edge; return the normalized current value when legal."""
    current_value = _value(current)
    target_value = _value(target)
    if not is_allowed(machine, current_value, target_value):
        raise TransitionNotAllowed(
            machine, current_value, target_value,
            f"Cannot {action} from {current_value} to {target_value}")
    return current_value


def _require_any(machine: str, current: object, allowed: Iterable[str],
                 reason: str) -> str:
    current_value = _value(current)
    if current_value not in {str(a) for a in allowed}:
        raise TransitionNotAllowed(machine, current_value, ",".join(sorted(
            {str(a) for a in allowed})), reason)
    return current_value


# ----------------------------------------------------------------------
# ContentCalendar guards (mirror ContentScheduler + publish gate)
# ----------------------------------------------------------------------
SCHEDULABLE = ("pending", "draft", "retry", "scheduled")
PUBLISHABLE = ("scheduled", "retry")


def require_schedulable(status: object) -> str:
    """Item may receive a date/time slot (assign_slot rule)."""
    current = _value(status)
    if current not in SCHEDULABLE:
        raise TransitionNotAllowed(
            "content", current, "scheduled",
            f"Cannot schedule content with status={current}")
    return current


def require_retryable(status: object) -> str:
    """Only FAILED items may re-enter the queue (request_retry rule)."""
    current = _value(status)
    if current != "failed":
        raise TransitionNotAllowed(
            "content", current, "retry",
            f"Only FAILED content can be retried (status={current})")
    return current


def require_publishable(item_status: Optional[object] = None,
                        run_status: Optional[object] = None) -> str:
    """Publish gate (content_calendar._require_publishable rule).

    Linked items (``run_status`` given) require an APPROVED run; unlinked
    items must already be SCHEDULED or RETRY. Message strings match the
    legacy gate exactly so API responses are unchanged.
    """
    if run_status is not None:
        current = _value(run_status)
        if current != "approved":
            raise TransitionNotAllowed(
                "pipeline", current, "published",
                f"Only APPROVED content can be published (run status={current})")
        return current
    current = _value(item_status)
    if current not in PUBLISHABLE:
        raise TransitionNotAllowed(
            "content", current, "published",
            f"Schedule the content first (status={current})")
    return current


# ----------------------------------------------------------------------
# Pipeline run guards (mirror CareerContentService._decide/_require_state)
# ----------------------------------------------------------------------
def require_review_decision(status: object) -> str:
    """Only runs awaiting review may be approved/rejected."""
    current = _value(status)
    if current != "pending_review":
        raise TransitionNotAllowed(
            "pipeline", current, "approved",
            f"Run is not awaiting review (status={current})")
    return current


def _editable_suffix(current: str) -> str:
    return "; approved runs are final" if current == "approved" else ""


def require_editable(status: object) -> str:
    """Draft may be human-edited while awaiting review (or failed)."""
    current = _value(status)
    if current not in ("pending_review", "failed"):
        raise TransitionNotAllowed(
            "pipeline", current, "pending_review",
            f"Run cannot be edited (status={current}{_editable_suffix(current)})")
    return current


def require_regenerable(status: object) -> str:
    """Draft may be regenerated while awaiting review, failed, or rejected."""
    current = _value(status)
    if current not in ("pending_review", "failed", "rejected"):
        raise TransitionNotAllowed(
            "pipeline", current, "pending_review",
            f"Run cannot be regenerated (status={current}{_editable_suffix(current)})")
    return current


def to_http_status(exc: TransitionNotAllowed) -> int:
    """Map a guard failure to its HTTP status (always 400: client state error)."""
    _ = exc
    return 400


def allowed_targets(machine: str, current: object) -> FrozenSet[str]:
    """Public alias for table lookup (introspection, UIs, dry-runs)."""
    from backend.state_machine.transitions import allowed_next

    return allowed_next(machine, current)


__all__ = [
    "TransitionNotAllowed",
    "require_transition",
    "require_schedulable",
    "require_retryable",
    "require_publishable",
    "require_review_decision",
    "require_editable",
    "require_regenerable",
    "to_http_status",
    "allowed_targets",
    "SCHEDULABLE",
    "PUBLISHABLE",
]
