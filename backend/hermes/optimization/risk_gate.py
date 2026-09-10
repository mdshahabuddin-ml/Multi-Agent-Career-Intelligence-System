"""
Risk gate: no risky decision is ever applied automatically.

Risk model (conservative by design):
- ``high`` — irreversible or externally visible: publish, schedule,
  delete, unpublish, edit published content, disconnect accounts, spend,
  or abandoning a platform / sharply changing cadence.
- ``medium`` — advisory but consequential: reprioritising a platform,
  changing format mix, retrying failed publishes.
- ``low`` — reversible, advisory-only: draft suggestions, watchlists,
  measurement reminders recorded to Hermes memory.

``classify`` marks every recommendation. ``apply_safe_only`` executes
ONLY low-risk advisory writes through an injected ``memory_store``
(no-op by default) and routes everything else to an injected
``approval_sink`` (Hermes ``ApprovalManager`` in production, a plain
list collector in tests). There is no code path that auto-applies a
medium/high recommendation — ``apply_safe_only`` enforces this even if
a caller mislabels a recommendation as auto-appliable.
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict, List, Tuple

from backend.hermes.optimization.schemas import ContentRecommendation

# Action verbs that always imply external visibility / irreversibility.
_HIGH_RISK_ACTIONS = frozenset({
    "publish", "schedule", "delete", "unpublish", "remove", "edit_published",
    "disconnect", "spend", "boost", "abandon_platform", "shift_cadence_sharply",
})

# Advisory-but-consequential actions: allowed to recommend, never to apply.
_MEDIUM_RISK_ACTIONS = frozenset({
    "reprioritise_platform", "change_format_mix", "retry_failed",
    "repost_topic", "change_posting_time",
})

# The ONLY action the loop may apply by itself: writing an advisory note.
_SAFE_ACTION = "record_suggestion"


def classify(rec: ContentRecommendation) -> ContentRecommendation:
    """Assign risk_level + requires_approval from the approval action.

    Callers may pre-label; classification is authoritative and can only
    escalate, never de-escalate, a risk label.
    """
    action = (rec.approval_action or "").strip().lower()
    if action in _HIGH_RISK_ACTIONS:
        rec.risk_level = "high"
        rec.requires_approval = True
    elif action in _MEDIUM_RISK_ACTIONS:
        if rec.risk_level == "low":
            rec.risk_level = "medium"
        rec.requires_approval = True
    elif action and action != _SAFE_ACTION:
        # Unknown future action: fail closed — needs a human.
        rec.risk_level = "high"
        rec.requires_approval = True
    else:
        rec.approval_action = _SAFE_ACTION
        if rec.risk_level != "low":
            rec.risk_level = "low"
        rec.requires_approval = False
    rec.auto_applied = False
    return rec


MemoryStore = Callable[[str, Dict[str, Any]], Awaitable[str]]
ApprovalSink = Callable[[ContentRecommendation], Awaitable[str]]


async def _noop_memory(agent_id: str, payload: Dict[str, Any]) -> str:
    return "noop"


async def _noop_approval(rec: ContentRecommendation) -> str:
    return "queued"


async def apply_safe_only(
    recommendations: List[ContentRecommendation],
    agent_id: str = "hermes-content-optimizer",
    memory_store: MemoryStore = _noop_memory,
    approval_sink: ApprovalSink = _noop_approval,
) -> Tuple[List[ContentRecommendation], List[ContentRecommendation]]:
    """Apply ONLY low-risk advisory recommendations; queue the rest.

    Returns ``(applied, queued)``. Medium/high items are NEVER passed to
    ``memory_store`` — even advisory-looking ones — they go exclusively
    to ``approval_sink``. This is the load-bearing safety property.
    """
    applied: List[ContentRecommendation] = []
    queued: List[ContentRecommendation] = []
    for rec in recommendations:
        classify(rec)
        if rec.requires_approval or rec.risk_level != "low":
            rec.auto_applied = False
            await approval_sink(rec)
            queued.append(rec)
        else:
            await memory_store(agent_id, {
                "area": rec.area,
                "suggestion": rec.suggestion,
                "rationale": rec.rationale,
                "evidence": rec.evidence.model_dump(),
                "confidence": rec.confidence,
            })
            rec.auto_applied = True
            applied.append(rec)
    return applied, queued
