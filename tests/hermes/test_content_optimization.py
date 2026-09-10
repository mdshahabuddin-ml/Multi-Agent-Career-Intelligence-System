"""
Tests for the Hermes content-optimization feedback loop.

Uses ``sample_content_history.py`` (10 deterministic posts) as the
historical analytics input. Guards:
- all 5 areas covered, every recommendation explainable,
- risky decisions are NEVER auto-applied,
- Career Intelligence recommendation code is untouched.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from backend.hermes.optimization import risk_gate
from backend.hermes.optimization.feedback_loop import HermesContentOptimizationLoop
from backend.hermes.optimization.schemas import ContentRecommendation, RecommendationEvidence
from backend.hermes.optimization.topic_analysis import analyse_topics, extract_topics
from tests.hermes.sample_content_history import sample_history

AREAS = {"topic_selection", "content_format", "posting_strategy",
         "platform_adaptation", "content_quality"}


@pytest.fixture
def rows():
    return sample_history()


@pytest.fixture
def loop():
    return HermesContentOptimizationLoop(window_days=30)


# ----------------------------------------------------------------------
# Topic analysis
# ----------------------------------------------------------------------
class TestTopicAnalysis:
    def test_hashtag_topics_extracted(self):
        row = {"title": "Python async await tutorial", "hashtags": ["python", "async"]}
        assert extract_topics(row, max_topics=2) == ["python", "async"]

    def test_title_fallback_skips_stopwords(self):
        topics = extract_topics({"title": "The Ultimate Guide to Kubernetes", "hashtags": []})
        assert "kubernetes" in topics
        assert "the" not in topics and "guide" not in topics

    def test_winning_topics_rank_first(self, rows):
        # NOTE: analyse_topics reads engagement_rate off the rows, which
        # analyse_performance computes — mirror the loop's call order here.
        from backend.content_analytics.analysis import analyse_performance
        analyse_performance(rows, total_published=len(rows), window_days=30)
        topics = analyse_topics(rows)
        by_name = {t.topic: t for t in topics}
        assert by_name["python"].measured_posts == 3
        assert by_name["resume"].measured_posts == 2
        assert by_name["resume"].avg_engagement_rate is not None
        assert by_name["resume"].avg_engagement_rate > (by_name["system-design"].avg_engagement_rate or 0)
        # Best multi-post topic (the loop's doubling-down candidate) is resume.
        multi = [t for t in topics if t.measured_posts >= 2 and t.avg_engagement_rate is not None]
        assert max(multi, key=lambda t: t.avg_engagement_rate or 0).topic == "resume"

    def test_unmeasured_posts_do_not_inflate_rates(self, rows):
        by_name = {t.topic: t for t in analyse_topics(rows)}
        # 'work'/'open' come only from the unmeasured LinkedIn post.
        assert by_name["open"].measured_posts == 0
        assert by_name["open"].avg_engagement_rate is None


# ----------------------------------------------------------------------
# Loop: 5 areas, explainable
# ----------------------------------------------------------------------
class TestLoopCoverage:
    def test_all_five_areas_covered(self, loop, rows):
        report = loop.analyse(rows)
        assert {r.area for r in report.recommendations} == AREAS

    def test_all_five_areas_covered_on_thin_input(self, loop, rows):
        thin = [rows[0], rows[2], rows[4]]  # one post per format/platform
        report = loop.analyse(thin)
        assert {r.area for r in report.recommendations} == AREAS

    def test_every_recommendation_explainable(self, loop, rows):
        report = loop.analyse(rows)
        assert report.recommendations, "loop emitted nothing"
        for rec in report.recommendations:
            assert rec.rationale.strip(), f"missing rationale: {rec.suggestion}"
            assert rec.evidence.sample_size > 0, f"empty evidence: {rec.suggestion}"
            assert rec.evidence.metric_values, f"no metric values: {rec.suggestion}"
            assert rec.confidence in ("high", "medium", "low")
            assert rec.risk_level in ("low", "medium", "high")

    def test_summary_counts_match_sample(self, loop, rows):
        report = loop.analyse(rows)
        assert report.summary.posts_analysed == 10
        assert report.summary.measured_posts == 8
        assert report.summary.unmeasured_posts == 2
        assert report.summary.recommendations_total == len(report.recommendations)

    def test_quality_flags_likes_without_comments(self, loop, rows):
        report = loop.analyse(rows)
        quality = report.for_area("content_quality")
        assert any("question" in r.suggestion.lower() or "replies" in " ".join(
            r.strengths if hasattr(r, "strengths") else "") or "question" in r.rationale.lower()
            for r in quality)

    def test_topic_followup_targets_winner(self, loop, rows):
        report = loop.analyse(rows)
        topic_recs = report.for_area("topic_selection")
        followups = [r for r in topic_recs if "follow-up" in r.suggestion]
        assert followups
        assert any(r.evidence.metric_values.get("topic") in ("resume", "python") for r in followups)


# ----------------------------------------------------------------------
# Risk gate: nothing risky auto-applies
# ----------------------------------------------------------------------
def _high_risk_rec() -> ContentRecommendation:
    return ContentRecommendation(
        area="platform_adaptation",
        suggestion="Publish 5 posts to instagram right now.",
        rationale="Test probe — must never execute without a human.",
        evidence=RecommendationEvidence(post_ids=[3], metric_values={"x": 1},
                                        sample_size=1, measured_posts=1),
        confidence="high",
        risk_level="low",  # deliberately mislabelled: gate must escalate
        approval_action="publish",
    )


class TestRiskGate:
    @pytest.mark.asyncio
    async def test_mislabelled_publish_is_queued_not_applied(self):
        stored, queued = [], []

        async def _memory(agent_id, payload):
            stored.append(payload)
            return "m1"

        async def _approval(rec):
            queued.append(rec)
            return "a1"

        applied, pending = await risk_gate.apply_safe_only(
            [_high_risk_rec()], memory_store=_memory, approval_sink=_approval)
        assert applied == [] and stored == []
        assert len(pending) == 1 and len(queued) == 1
        assert pending[0].risk_level == "high" and pending[0].requires_approval

    @pytest.mark.asyncio
    async def test_loop_run_applies_only_low_risk(self, loop, rows):
        stored, queued = [], []

        async def _memory(agent_id, payload):
            stored.append(payload)
            return "m"

        async def _approval(rec):
            queued.append(rec)
            return "a"

        report = await loop.run(rows, memory_store=_memory, approval_sink=_approval)
        assert all(r.risk_level == "low" and not r.requires_approval for r in report.applied)
        assert all(r.auto_applied for r in report.applied)
        assert all(not r.auto_applied for r in report.approvals)
        assert all(r.requires_approval or r.risk_level != "low" for r in report.approvals)
        # Nothing applied touched publishing/scheduling/deleting.
        assert report.applied and report.approvals
        for rec in report.applied:
            assert rec.approval_action == "record_suggestion"

    def test_unknown_action_fails_closed(self):
        rec = ContentRecommendation(
            area="content_format", suggestion="Do something novel.", rationale="Probe.",
            evidence=RecommendationEvidence(post_ids=[1], metric_values={"x": 1},
                                            sample_size=1, measured_posts=1),
            approval_action="future_action_xyz")
        assert risk_gate.classify(rec).requires_approval
        assert rec.risk_level == "high"


# ----------------------------------------------------------------------
# Isolation: Career Intelligence untouched
# ----------------------------------------------------------------------
class TestCareerIsolation:
    def test_optimization_package_has_no_career_imports(self):
        root = Path(__file__).resolve().parents[2] / "backend" / "hermes" / "optimization"
        offenders = []
        for path in sorted(root.glob("*.py")):
            for line in path.read_text(encoding="utf-8").splitlines():
                stripped = line.strip()
                if not stripped.startswith(("import ", "from ")):
                    continue  # docstrings/comments explaining isolation are fine
                lowered = stripped.lower()
                if ("career_service" in lowered or "agents.career" in lowered
                        or "personalization_service" in lowered
                        or "careeradvisor" in lowered or "learningagent" in lowered):
                    offenders.append(f"{path.name}: {stripped}")
        assert offenders == [], f"career coupling: {offenders}"

    def test_api_router_has_no_career_imports(self):
        path = Path(__file__).resolve().parents[2] / "backend" / "api" / "hermes_optimization.py"
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith(("import ", "from ")):
                assert "career" not in stripped.lower(), f"career import: {stripped}"

    def test_career_recommenders_still_importable(self):
        # Career Intelligence algorithms exist and are untouched by this loop.
        from backend.agents.career.career_advisor import CareerAdvisor  # noqa: F401
        from backend.agents.career.learning_agent import LearningAgent  # noqa: F401
        from backend.services.career_service import CareerService  # noqa: F401
