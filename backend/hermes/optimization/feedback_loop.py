"""
Hermes content-optimization feedback loop.

Historical performance → explainable recommendations across 5 areas:
    topic_selection · content_format · posting_strategy ·
    platform_adaptation · content_quality

Safety properties (load-bearing):
1. Advisory only — the loop NEVER publishes, schedules, edits or deletes
   anything. Acting on a recommendation requires a human approval.
2. Risk gate — medium/high recommendations are routed to an approval
   sink; only low-risk advisory notes are recorded to Hermes memory.
3. Explainable — every recommendation carries rationale + measured
   evidence (post ids, values, sample size) + confidence from sample
   size. Thin evidence → "measure first", never a guess.
4. Official-API-only — consumes ``ContentAnalyticsService.latest_per_post``
   rows (or equivalent dicts); unsupported metrics stay ``None``.

Career Intelligence is untouched: this module imports ONLY
``backend.content_analytics`` and ``backend.hermes`` — never
``backend.agents.career``, ``career_service`` or personalization.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from backend.content_analytics.analysis import analyse_performance
from backend.content_analytics.feedback import feedback_for_portfolio
from backend.hermes.optimization import risk_gate
from backend.hermes.optimization.schemas import (
    Area,
    ContentRecommendation,
    LoopRunSummary,
    OptimizationReport,
    RecommendationEvidence,
    TopicPerformance,
)
from backend.hermes.optimization.topic_analysis import analyse_topics
from backend.observability import span
from backend.observability.conventions import (
    ATTR_FLOW,
    ATTR_LAYER,
    LAYER_HERMES,
    SPAN_KIND_AGENT,
)

Confidence = str


def _num(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _confidence(measured: int, total: int) -> Confidence:
    """Confidence from sample size; unmeasured-heavy evidence caps at low."""
    if total and (total - measured) > measured:
        return "low"
    if measured >= 8:
        return "high"
    if measured >= 4:
        return "medium"
    return "low"


def _evidence(rows: List[Dict[str, Any]], metric_values: Dict[str, Any],
              window_days: int) -> RecommendationEvidence:
    measured = sum(1 for r in rows if any(
        r.get(k) is not None for k in ("likes", "comments", "shares", "views", "impressions")))
    return RecommendationEvidence(
        post_ids=[int(r["content_id"]) for r in rows if r.get("content_id") is not None][:8],
        metric_values=metric_values,
        sample_size=len(rows),
        measured_posts=measured,
        unmeasured_posts=len(rows) - measured,
        window_days=window_days,
    )


def _rec(area: Area, suggestion: str, rationale: str, evidence: RecommendationEvidence,
         approval_action: str, risk_hint: str = "low") -> ContentRecommendation:
    """Build a recommendation; risk_gate.classify remains authoritative."""
    rec = ContentRecommendation(
        area=area,
        suggestion=suggestion,
        rationale=rationale,
        evidence=evidence,
        confidence=_confidence(evidence.measured_posts, evidence.sample_size),
        risk_level=risk_hint,  # type: ignore[assignment] — gate escalates, never de-escalates
        requires_approval=risk_hint != "low",
        approval_action=approval_action,
    )
    return risk_gate.classify(rec)


class HermesContentOptimizationLoop:
    """Historical content performance → 5-area optimization recommendations."""

    AREAS: List[Area] = [
        "topic_selection",
        "content_format",
        "posting_strategy",
        "platform_adaptation",
        "content_quality",
    ]

    def __init__(self, window_days: int = 30,
                 agent_id: str = "hermes-content-optimizer") -> None:
        self.window_days = window_days
        self.agent_id = agent_id

    # ------------------------------------------------------------------
    # Public entry points
    # ------------------------------------------------------------------
    def analyse(self, rows: List[Dict[str, Any]]) -> OptimizationReport:
        """Pure analysis: recommendations + risk labels, NO writes, NO applies."""
        # Observability span (no-op unless OTEL_ENABLED=true); never affects logic.
        with span("hermes.optimization.analyse", kind=SPAN_KIND_AGENT, attributes={
            ATTR_LAYER: LAYER_HERMES, ATTR_FLOW: "optimization_analyse",
            "posts_analysed": len(rows),
        }):
            return self._analyse_inner([dict(r) for r in rows])

    def _analyse_inner(self, rows: List[Dict[str, Any]]) -> OptimizationReport:
        rows = [dict(r) for r in rows]
        performance = analyse_performance(rows, total_published=len(rows),
                                          window_days=self.window_days)
        topics = analyse_topics(rows)
        portfolio = feedback_for_portfolio(rows)

        recommendations: List[ContentRecommendation] = []
        recommendations += self._topic_recommendations(rows, topics)
        recommendations += self._format_recommendations(rows, performance)
        recommendations += self._posting_recommendations(rows, performance)
        recommendations += self._platform_recommendations(rows, performance)
        recommendations += self._quality_recommendations(rows, portfolio)

        approvals = [r for r in recommendations if r.requires_approval or r.risk_level != "low"]
        measured = sum(1 for r in rows if any(
            r.get(k) is not None for k in ("likes", "comments", "shares", "views", "impressions")))
        return OptimizationReport(
            recommendations=recommendations,
            topics=topics,
            approvals=approvals,
            applied=[],
            summary=LoopRunSummary(
                posts_analysed=len(rows),
                measured_posts=measured,
                unmeasured_posts=len(rows) - measured,
                recommendations_total=len(recommendations),
                auto_applied=0,
                queued_for_approval=len(approvals),
                generated_at=datetime.now(timezone.utc),
            ),
        )

    async def run(
        self,
        rows: List[Dict[str, Any]],
        memory_store: risk_gate.MemoryStore | None = None,
        approval_sink: risk_gate.ApprovalSink | None = None,
    ) -> OptimizationReport:
        """Full loop: analyse → risk-gate → safe-apply only.

        Risky items are queued via ``approval_sink`` (defaults to creating
        a Hermes ``ApprovalManager`` request) and NEVER executed.
        """
        # Observability span (no-op unless OTEL_ENABLED=true); never affects logic.
        async with span("hermes.optimization.run", kind=SPAN_KIND_AGENT, attributes={
            ATTR_LAYER: LAYER_HERMES, ATTR_FLOW: "optimization_run",
            "posts_analysed": len(rows),
        }):
            return await self._run_inner(rows, memory_store, approval_sink)

    async def _run_inner(
        self,
        rows: List[Dict[str, Any]],
        memory_store: risk_gate.MemoryStore | None = None,
        approval_sink: risk_gate.ApprovalSink | None = None,
    ) -> OptimizationReport:
        report = self.analyse(rows)
        store = memory_store or risk_gate._noop_memory
        sink = approval_sink or self._default_approval_sink()
        applied, queued = await risk_gate.apply_safe_only(
            report.recommendations, agent_id=self.agent_id,
            memory_store=store, approval_sink=sink,
        )
        report.applied = applied
        report.approvals = queued
        report.summary.auto_applied = len(applied)
        report.summary.queued_for_approval = len(queued)
        report.summary.generated_at = datetime.now(timezone.utc)
        return report

    def _default_approval_sink(self) -> risk_gate.ApprovalSink:
        async def _sink(rec: ContentRecommendation) -> str:
            from backend.hermes.approval.manager import ApprovalManager

            manager = ApprovalManager()
            request = manager.request_approval(
                action=rec.approval_action or "content_optimization",
                description=f"[{rec.area}] {rec.suggestion} — {rec.rationale}",
                requester_id=self.agent_id,
                data={"area": rec.area, "suggestion": rec.suggestion,
                      "evidence": rec.evidence.model_dump(), "risk_level": rec.risk_level},
            )
            return request.id

        return _sink

    # ------------------------------------------------------------------
    # 1. Topic selection (needs measured topics; else measure-first)
    # ------------------------------------------------------------------
    def _topic_recommendations(self, rows: List[Dict[str, Any]],
                               topics: List[TopicPerformance]) -> List[ContentRecommendation]:
        recs: List[ContentRecommendation] = []
        measured_topics = [t for t in topics if t.measured_posts > 0 and t.avg_engagement_rate is not None]
        if not measured_topics:
            recs.append(_rec(
                "topic_selection",
                "Refresh analytics before choosing topics — no measured topic yet.",
                "Topic advice without measured engagement would be a guess; "
                f"{len(rows)} post(s) analysed but none has a supported engagement signal.",
                _evidence(rows, {"measured_topics": 0}, self.window_days),
                approval_action="record_suggestion",
            ))
            return recs
        winner = measured_topics[0]
        multi_post = [t for t in measured_topics if t.measured_posts >= 2]
        if multi_post:
            winner = multi_post[0]
            recs.append(_rec(
                "topic_selection",
                f"Draft the next post as a follow-up on '{winner.topic}'.",
                f"'{winner.topic}' leads multi-post topics at {winner.avg_engagement_rate}% avg engagement "
                f"across {winner.measured_posts} measured post(s); compounding winners beats chasing new topics.",
                _evidence(
                    [r for r in rows if r.get("content_id") in winner.post_ids],
                    {"topic": winner.topic, "avg_engagement_rate": winner.avg_engagement_rate,
                     "measured_posts": winner.measured_posts, "platforms": winner.platforms},
                    self.window_days,
                ),
                approval_action="repost_topic",
                risk_hint="medium",
            ))
        else:
            # Single-post spikes are not doubling-down evidence — watchlist only.
            leader = winner
            recs.append(_rec(
                "topic_selection",
                f"Watch '{leader.topic}' — early leader on thin evidence, do not double down yet.",
                f"'{leader.topic}' shows {leader.avg_engagement_rate}% from a single measured post; "
                "one post is noise, not a pattern. A second post on the topic buys real evidence.",
                _evidence(
                    [r for r in rows if r.get("content_id") in leader.post_ids],
                    {"topic": leader.topic, "avg_engagement_rate": leader.avg_engagement_rate,
                     "measured_posts": leader.measured_posts},
                    self.window_days,
                ),
                approval_action="record_suggestion",
            ))
        strugglers = [t for t in measured_topics
                      if t.measured_posts >= 2 and (t.avg_engagement_rate or 0) < 1.0]
        if strugglers:
            worst = strugglers[-1]
            recs.append(_rec(
                "topic_selection",
                f"Rest '{worst.topic}' for two weeks instead of repeating it now.",
                f"'{worst.topic}' averages {worst.avg_engagement_rate}% over {worst.measured_posts} measured "
                "posts — repeating it unchanged risks more low-engagement inventory. Resting is reversible.",
                _evidence(
                    [r for r in rows if r.get("content_id") in worst.post_ids],
                    {"topic": worst.topic, "avg_engagement_rate": worst.avg_engagement_rate,
                     "measured_posts": worst.measured_posts},
                    self.window_days,
                ),
                approval_action="repost_topic",
                risk_hint="medium",
            ))
        untagged = sum(1 for r in rows if not (r.get("hashtags") or []))
        if untagged > len(rows) / 2 and len(rows) >= 3:
            recs.append(_rec(
                "topic_selection",
                "Add 2–3 topic hashtags to future posts so topic attribution improves.",
                f"{untagged} of {len(rows)} posts carry no hashtags, so topic analysis falls back to "
                "title keywords — weaker evidence for future topic calls.",
                _evidence(rows, {"posts_without_hashtags": untagged}, self.window_days),
                approval_action="record_suggestion",
            ))
        return recs

    # ------------------------------------------------------------------
    # 2. Content format (uses by_content_type breakdown)
    # ------------------------------------------------------------------
    def _format_recommendations(self, rows: List[Dict[str, Any]],
                                performance: Any) -> List[ContentRecommendation]:
        recs: List[ContentRecommendation] = []
        measured_types = {k: v for k, v in performance.by_content_type.items() if v.measured_posts > 0}
        if not measured_types:
            recs.append(_rec(
                "content_format",
                "Hold format mix steady until formats are measurable.",
                "No content type has a supported metric yet — changing the mix now hides what works.",
                _evidence(rows, {"measured_formats": 0}, self.window_days),
                approval_action="record_suggestion",
            ))
            return recs
        best = max(measured_types.items(),
                   key=lambda kv: (kv[1].avg_engagement_rate is not None,
                                   kv[1].avg_engagement_rate or -1.0))
        name, breakdown = best
        if breakdown.avg_engagement_rate is not None and breakdown.measured_posts >= 2:
            recs.append(_rec(
                "content_format",
                f"Weight the next 3–5 posts toward '{name}' format.",
                f"'{name}' leads formats at {breakdown.avg_engagement_rate}% avg engagement over "
                f"{breakdown.measured_posts} measured post(s). Shifting the mix changes output, so it needs approval.",
                _evidence(
                    [r for r in rows if str(r.get("content_type")) == name],
                    {"format": name, "avg_engagement_rate": breakdown.avg_engagement_rate,
                     "measured_posts": breakdown.measured_posts},
                    self.window_days,
                ),
                approval_action="change_format_mix",
                risk_hint="medium",
            ))
        elif breakdown.avg_engagement_rate is not None:
            # Single-sample lead: watchlist note, not a mix change.
            recs.append(_rec(
                "content_format",
                f"Watch '{name}' — early format lead on thin evidence, hold the mix.",
                f"'{name}' shows {breakdown.avg_engagement_rate}% from a single measured post; "
                "one sample cannot justify a format shift. A second measured post buys the evidence.",
                _evidence(
                    [r for r in rows if str(r.get("content_type")) == name],
                    {"format": name, "avg_engagement_rate": breakdown.avg_engagement_rate,
                     "measured_posts": breakdown.measured_posts},
                    self.window_days,
                ),
                approval_action="record_suggestion",
            ))
        return recs

    # ------------------------------------------------------------------
    # 3. Posting strategy (cadence + weekday; timestamps optional)
    # ------------------------------------------------------------------
    def _posting_recommendations(self, rows: List[Dict[str, Any]],
                                 performance: Any) -> List[ContentRecommendation]:
        recs: List[ContentRecommendation] = []
        stamped = [(r, self._as_dt(r.get("published_at"))) for r in rows]
        stamped = [(r, dt) for r, dt in stamped if dt is not None]
        if len(stamped) < 4:
            recs.append(_rec(
                "posting_strategy",
                "Keep a steady weekly cadence until timing evidence accumulates.",
                f"Only {len(stamped)} of {len(rows)} posts carry usable publish timestamps — "
                "weekday/cadence advice now would be noise. Publish weekly; the loop re-evaluates with data.",
                _evidence(rows, {"posts_with_timestamps": len(stamped)}, self.window_days),
                approval_action="record_suggestion",
            ))
            return recs
        days = sorted(dt for _, dt in stamped)
        span_days = max(1, (days[-1] - days[0]).days or 1)
        per_week = round(len(stamped) / (span_days / 7), 2)
        by_weekday: Dict[str, List[float]] = defaultdict(list)
        for r, dt in stamped:
            rate = _num(r.get("engagement_rate"))
            if rate is not None:
                by_weekday[dt.strftime("%A")].append(rate)
        weekday_avg = {day: round(sum(v) / len(v), 2) for day, v in by_weekday.items() if len(v) >= 2}
        if weekday_avg:
            best_day = max(weekday_avg, key=lambda d: weekday_avg[d])
            recs.append(_rec(
                "posting_strategy",
                f"Trial the next 2 posts on {best_day} (current cadence ~{per_week}/week).",
                f"{best_day} averages {weekday_avg[best_day]}% engagement across "
                f"{len(by_weekday[best_day])} measured post(s) at ~{per_week} posts/week. "
                "A time shift affects scheduling, so it needs approval — this is a trial, not a migration.",
                _evidence(
                    [r for r, dt in stamped if dt.strftime("%A") == best_day],
                    {"best_weekday": best_day, "weekday_avg_rate": weekday_avg[best_day],
                     "posts_per_week": per_week},
                    self.window_days,
                ),
                approval_action="change_posting_time",
                risk_hint="medium",
            ))
        elif per_week < 1.0:
            recs.append(_rec(
                "posting_strategy",
                "Raise cadence toward 1 post/week; current pace is too thin to learn from.",
                f"~{per_week} posts/week over {span_days} days yields too few samples — "
                "volume here buys evidence, but cadence changes affect workload, so approve first.",
                _evidence(rows, {"posts_per_week": per_week, "span_days": span_days}, self.window_days),
                approval_action="change_posting_time",
                risk_hint="medium",
            ))
        else:
            recs.append(_rec(
                "posting_strategy",
                f"Hold the current ~{per_week}/week cadence; no weekday stands out yet.",
                "No weekday has 2+ measured posts, so timing changes would be guesses. "
                "Consistency now buys the data for a real timing call later.",
                _evidence(rows, {"posts_per_week": per_week}, self.window_days),
                approval_action="record_suggestion",
            ))
        return recs

    @staticmethod
    def _as_dt(value: Any) -> Optional[datetime]:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        try:
            return datetime.fromisoformat(str(value))
        except ValueError:
            return None

    # ------------------------------------------------------------------
    # 4. Platform adaptation (reprioritise ok w/ approval; abandon = high)
    # ------------------------------------------------------------------
    def _platform_recommendations(self, rows: List[Dict[str, Any]],
                                  performance: Any) -> List[ContentRecommendation]:
        recs: List[ContentRecommendation] = []
        measured_platforms = {k: v for k, v in performance.by_platform.items() if v.measured_posts > 0}
        unmeasured = [k for k, v in performance.by_platform.items() if v.measured_posts == 0]
        if measured_platforms:
            best = max(measured_platforms.items(),
                       key=lambda kv: (kv[1].avg_engagement_rate is not None,
                                       kv[1].avg_engagement_rate or -1.0))
            name, breakdown = best
            if breakdown.avg_engagement_rate is not None:
                recs.append(_rec(
                    "platform_adaptation",
                    f"Adapt the next posts for {name} first (format + hooks native to it).",
                    f"{name} leads platforms at {breakdown.avg_engagement_rate}% over "
                    f"{breakdown.measured_posts} measured post(s). Reprioritising reach needs approval.",
                    _evidence(
                        [r for r in rows if str(r.get("platform")) == name],
                        {"platform": name, "avg_engagement_rate": breakdown.avg_engagement_rate,
                         "measured_posts": breakdown.measured_posts},
                        self.window_days,
                    ),
                    approval_action="reprioritise_platform",
                    risk_hint="medium",
                ))
            # Abandonment: deliberately strict — 5+ measured, all weak, a strong alternative exists.
            for pname, pbreak in measured_platforms.items():
                if pname == name or pbreak.measured_posts < 5:
                    continue
                if (pbreak.avg_engagement_rate or 0) < 1.0 and (breakdown.avg_engagement_rate or 0) >= 5.0:
                    rec = _rec(
                        "platform_adaptation",
                        f"Consider pausing {pname} after human review — NOT automatic.",
                        f"{pname} averages {pbreak.avg_engagement_rate}% over {pbreak.measured_posts} measured "
                        f"posts while {name} hits {breakdown.avg_engagement_rate}%. Pausing a channel is "
                        "high-risk (audience loss) — this recommendation only proposes the review.",
                        _evidence(
                            [r for r in rows if str(r.get("platform")) == pname],
                            {"platform": pname, "avg_engagement_rate": pbreak.avg_engagement_rate,
                             "measured_posts": pbreak.measured_posts, "alternative": name},
                            self.window_days,
                        ),
                        approval_action="abandon_platform",
                        risk_hint="high",
                    )
                    recs.append(rec)
        for pname in sorted(unmeasured):
            recs.append(_rec(
                "platform_adaptation",
                f"Judge {pname} inside its native analytics, not against measured platforms.",
                f"{pname} has posts but zero supported metrics via official APIs — "
                "ranking it here would punish it for a data gap, not performance.",
                _evidence(
                    [r for r in rows if str(r.get("platform")) == pname],
                    {"platform": pname, "measured_posts": 0},
                    self.window_days,
                ),
                approval_action="record_suggestion",
            ))
        if not measured_platforms:
            recs.append(_rec(
                "platform_adaptation",
                "Refresh analytics before adapting anything per platform.",
                "No platform has a supported metric yet — platform calls now would be guesses.",
                _evidence(rows, {"measured_platforms": 0}, self.window_days),
                approval_action="record_suggestion",
            ))
        return recs

    # ------------------------------------------------------------------
    # 5. Content quality (craft notes — low risk, auto-appliable as notes)
    # ------------------------------------------------------------------
    def _quality_recommendations(self, rows: List[Dict[str, Any]],
                                 portfolio: Any) -> List[ContentRecommendation]:
        recs: List[ContentRecommendation] = []
        per_post = getattr(portfolio, "per_post", []) or []
        by_verdict: Dict[str, int] = defaultdict(int)
        for item in per_post:
            by_verdict[getattr(item, "verdict", "unmeasured")] += 1
        zero_comment = [
            r for r in rows
            if (_num(r.get("likes")) or 0) > 0 and (_num(r.get("comments")) or 0) == 0
            and r.get("likes") is not None and r.get("comments") is not None
        ]
        if zero_comment:
            recs.append(_rec(
                "content_quality",
                "End the next 2 posts with a direct question to convert likes into replies.",
                f"{len(zero_comment)} measured post(s) earn likes but zero comments — "
                "the hook works, the conversation prompt is missing. Craft-only change, fully reversible.",
                _evidence(zero_comment, {"posts_with_likes_no_comments": len(zero_comment)},
                          self.window_days),
                approval_action="record_suggestion",
            ))
        if by_verdict.get("needs_attention", 0) >= 2:
            weak = [r for r in rows if (_num(r.get("engagement_rate")) or 99) < 1.0
                    and r.get("engagement_rate") is not None]
            recs.append(_rec(
                "content_quality",
                "Tighten hooks: first 2 lines carry the payoff, cut throat-clearing openers.",
                f"{by_verdict['needs_attention']} post(s) sit below 1% engagement — "
                "the consistent pattern is weak openings, not topics. Reversible edit to future drafts only.",
                _evidence(weak or rows, {"needs_attention_posts": by_verdict["needs_attention"]},
                          self.window_days),
                approval_action="record_suggestion",
            ))
        strong = [getattr(item, "content_id", None) for item in per_post
                  if getattr(item, "verdict", "") == "strong"]
        if strong:
            recs.append(_rec(
                "content_quality",
                "Replicate the strong posts' structure (hook → proof → CTA) in the next draft.",
                f"{len(strong)} strong post(s) prove the structure works — "
                "copying structure into a new draft risks nothing already published.",
                _evidence(
                    [r for r in rows if r.get("content_id") in set(strong)],
                    {"strong_posts": len(strong)},
                    self.window_days,
                ),
                approval_action="record_suggestion",
            ))
        if not recs:
            recs.append(_rec(
                "content_quality",
                "No quality pattern is actionable yet — keep hooks tight and re-run after refresh.",
                "Measured quality signals are too thin to name a pattern; "
                "saying more would overstate the evidence.",
                _evidence(rows, {"verdicts": dict(by_verdict)}, self.window_days),
                approval_action="record_suggestion",
            ))
        return recs
