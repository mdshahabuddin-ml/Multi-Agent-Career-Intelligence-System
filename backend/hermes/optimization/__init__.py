"""
Hermes content-optimization feedback loop.

Historical official-API performance → explainable recommendations across
topic_selection / content_format / posting_strategy / platform_adaptation /
content_quality — with a risk gate: NOTHING risky is ever auto-applied.

Isolation contract (do not break):
- Imports ONLY ``backend.content_analytics`` and ``backend.hermes``.
- NEVER imports ``backend.agents.career``, ``career_service``,
  ``personalization_service`` or any career table/model. Career
  Intelligence recommendation algorithms are untouched.
"""

from backend.hermes.optimization.feedback_loop import HermesContentOptimizationLoop
from backend.hermes.optimization import risk_gate
from backend.hermes.optimization.schemas import (
    ContentRecommendation,
    LoopRunSummary,
    OptimizationReport,
    RecommendationEvidence,
    TopicPerformance,
)
from backend.hermes.optimization.topic_analysis import analyse_topics, extract_topics

__all__ = [
    "HermesContentOptimizationLoop",
    "risk_gate",
    "ContentRecommendation",
    "LoopRunSummary",
    "OptimizationReport",
    "RecommendationEvidence",
    "TopicPerformance",
    "analyse_topics",
    "extract_topics",
]

__version__ = "0.1.0"
