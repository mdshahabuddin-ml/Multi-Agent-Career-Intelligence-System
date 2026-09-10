"""
Central state machine: transition rules + guards for existing lifecycles.

Phase implemented: Existing State Machine → Transition Rules → Central
Guards → Tests.

- ``transitions.py`` — canonical allowed-edge tables derived from observed
  writer code (scheduler, publishing service, pipeline service, approval
  manager). Pure data + ``is_allowed`` / ``allowed_next`` / ``is_terminal``.
- ``guards.py`` — single enforcement point. Messages match the legacy
  call sites exactly; ``TransitionNotAllowed`` subclasses ``ValueError``
  so existing ``except ValueError`` handlers keep working.

Rule: new lifecycle checks MUST use these guards instead of re-implementing
status comparisons inline.
"""

from backend.state_machine.guards import (
    PUBLISHABLE,
    SCHEDULABLE,
    TransitionNotAllowed,
    allowed_targets,
    require_editable,
    require_publishable,
    require_regenerable,
    require_retryable,
    require_review_decision,
    require_schedulable,
    require_transition,
    to_http_status,
)
from backend.state_machine.transitions import (
    AGENT_LIFECYCLE_TRANSITIONS,
    APPROVAL_STATUS_TRANSITIONS,
    CONTENT_STATUS_TRANSITIONS,
    MACHINES,
    PIPELINE_STAGE_TRANSITIONS,
    allowed_next,
    is_allowed,
    is_terminal,
)

__all__ = [
    "PUBLISHABLE",
    "SCHEDULABLE",
    "TransitionNotAllowed",
    "allowed_targets",
    "require_editable",
    "require_publishable",
    "require_regenerable",
    "require_retryable",
    "require_review_decision",
    "require_schedulable",
    "require_transition",
    "to_http_status",
    "AGENT_LIFECYCLE_TRANSITIONS",
    "APPROVAL_STATUS_TRANSITIONS",
    "CONTENT_STATUS_TRANSITIONS",
    "MACHINES",
    "PIPELINE_STAGE_TRANSITIONS",
    "allowed_next",
    "is_allowed",
    "is_terminal",
]

__version__ = "0.1.0"
