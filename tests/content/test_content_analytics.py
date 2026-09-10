"""
Tests for the isolated content-analytics layer.

Covers the full pipeline:
    Published Content → Analytics → Performance Analysis → Feedback → Optimization

Isolation guard: no test here may import career modules; a dedicated test
asserts the content_analytics package has zero career imports.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from backend.content_analytics import capabilities
from backend.content_analytics.analysis import analyse_performance, compute_engagement_rate
from backend.content_analytics.feedback import feedback_for_portfolio, feedback_for_post
from backend.content_analytics.optimizer import build_optimization_plan
from backend.content_analytics.providers import (
    AnalyticsUnsupportedError,
    fetch_facebook,
    fetch_instagram,
    fetch_linkedin,
    fetch_metrics,
    fetch_youtube,
)
from backend.content_analytics.schemas import PerformanceSummary


def _mock_client(responses: list[httpx.Response]) -> MagicMock:
    client = MagicMock(spec=httpx.AsyncClient)
    queue = list(responses)

    async def _get(*args, **kwargs):
        return queue.pop(0)

    client.get = AsyncMock(side_effect=_get)
    return client


def _resp(status: int, payload: dict) -> httpx.Response:
    return httpx.Response(status, content=json.dumps(payload).encode(), request=httpx.Request("GET", "https://x.test"))


# ----------------------------------------------------------------------
# Capabilities: official-API-only contract
# ----------------------------------------------------------------------
class TestCapabilities:
    def test_publishing_status_always_supported(self):
        for platform in ["youtube", "instagram", "facebook", "linkedin", "twitter", "tiktok", "unknown"]:
            assert capabilities.is_metric_supported(platform, "publishing_status") is True

    def test_youtube_only_statistics(self):
        assert capabilities.is_metric_supported("youtube", "views")
        assert capabilities.is_metric_supported("youtube", "likes")
        assert capabilities.is_metric_supported("youtube", "comments")
        # Data API v3 has no impressions/shares — must be unsupported, not zero.
        assert not capabilities.is_metric_supported("youtube", "impressions")
        assert not capabilities.is_metric_supported("youtube", "shares")
        assert not capabilities.is_metric_supported("youtube", "reach")

    def test_instagram_rich_but_no_clicks(self):
        assert capabilities.is_metric_supported("instagram", "impressions")
        assert capabilities.is_metric_supported("instagram", "saves")
        assert not capabilities.is_metric_supported("instagram", "clicks")

    def test_unsupported_platform_status_only(self):
        assert capabilities.supported_metrics_for("twitter") == ["publishing_status"]
        assert capabilities.supported_metrics_for("tiktok") == ["publishing_status"]
        assert "likes" in capabilities.unsupported_metrics_for("twitter")

    def test_supported_unsupported_partition(self):
        for platform in ["youtube", "instagram", "facebook", "linkedin"]:
            supported = set(capabilities.supported_metrics_for(platform))
            unsupported = set(capabilities.unsupported_metrics_for(platform))
            assert supported | unsupported == set(capabilities.TRACKED_METRICS)
            assert supported & unsupported == set()


# ----------------------------------------------------------------------
# Providers: official endpoints, None for unsupported
# ----------------------------------------------------------------------
class TestYouTubeProvider:
    @pytest.mark.asyncio
    async def test_maps_statistics_and_leaves_unsupported_none(self):
        client = _mock_client([_resp(200, {"items": [{"statistics": {
            "viewCount": "1000", "likeCount": "50", "commentCount": "5"}}]})])
        out = await fetch_youtube("tok", "vid123", client)
        assert out["views"] == 1000
        assert out["likes"] == 50
        assert out["comments"] == 5
        assert out["impressions"] is None
        assert out["shares"] is None

    @pytest.mark.asyncio
    async def test_missing_video_raises_not_found(self):
        from backend.content_analytics.providers import AnalyticsNotFoundError

        client = _mock_client([_resp(200, {"items": []})])
        with pytest.raises(AnalyticsNotFoundError):
            await fetch_youtube("tok", "missing", client)


class TestInstagramProvider:
    @pytest.mark.asyncio
    async def test_media_plus_insights(self):
        client = _mock_client([
            _resp(200, {"like_count": 120, "comments_count": 9}),
            _resp(200, {"data": [
                {"name": "impressions", "values": [{"value": 5000}]},
                {"name": "reach", "values": [{"value": 4000}]},
                {"name": "shares", "values": [{"value": 11}]},
                {"name": "saves", "values": [{"value": 7}]},
            ]}),
        ])
        out = await fetch_instagram("tok", "media1", client)
        assert out["likes"] == 120
        assert out["impressions"] == 5000
        assert out["shares"] == 11
        assert out["clicks"] is None  # never exposed → None

    @pytest.mark.asyncio
    async def test_insights_gated_degrades_gracefully(self):
        client = _mock_client([
            _resp(200, {"like_count": 10, "comments_count": 1}),
            _resp(403, {"error": {"message": "permission denied"}}),
        ])
        out = await fetch_instagram("tok", "media1", client)
        assert out["likes"] == 10
        assert out["impressions"] is None


class TestFacebookProvider:
    @pytest.mark.asyncio
    async def test_post_fields_plus_insights(self):
        client = _mock_client([
            _resp(200, {"likes": {"summary": {"total_count": 30}},
                        "comments": {"summary": {"total_count": 4}},
                        "shares": {"count": 2}}),
            _resp(200, {"data": [
                {"name": "post_impressions", "values": [{"value": 900}]},
                {"name": "post_impressions_unique", "values": [{"value": 700}]},
            ]}),
        ])
        out = await fetch_facebook("tok", "post1", client)
        assert out["likes"] == 30
        assert out["shares"] == 2
        assert out["impressions"] == 900
        assert out["reach"] == 700
        assert out["saves"] is None


class TestLinkedInProvider:
    @pytest.mark.asyncio
    async def test_limited_visibility_returns_none_not_zero(self):
        client = _mock_client([_resp(404, {})])
        out = await fetch_linkedin("tok", "urn:li:share:123", client)
        assert out["likes"] is None
        assert out["comments"] is None
        assert out["impressions"] is None


class TestDispatcher:
    @pytest.mark.asyncio
    async def test_unsupported_platform_raises(self):
        with pytest.raises(AnalyticsUnsupportedError):
            await fetch_metrics("twitter", "tok", "123")

    @pytest.mark.asyncio
    async def test_missing_post_id_raises(self):
        with pytest.raises(AnalyticsUnsupportedError):
            await fetch_metrics("youtube", "tok", "")

    @pytest.mark.asyncio
    async def test_safety_net_strips_unsupported(self):
        client = _mock_client([_resp(200, {"items": [{"statistics": {
            "viewCount": "10", "likeCount": "1", "commentCount": "0"}}]})])
        out = await fetch_metrics("youtube", "tok", "vid", client)
        assert out["impressions"] is None  # enforced even if a provider leaked one


# ----------------------------------------------------------------------
# Analysis: None-aware aggregation
# ----------------------------------------------------------------------
def _row(cid: int, platform: str, **metrics):
    base = {"content_id": cid, "title": f"Post {cid}", "platform": platform,
            "content_type": "post", "supported_metrics": [], "unsupported_metrics": []}
    base.update(metrics)
    return base


class TestAnalysis:
    def test_engagement_rate_prefers_impressions(self):
        assert compute_engagement_rate({"likes": 10, "comments": 5, "shares": 5, "impressions": 1000}) == 2.0

    def test_engagement_rate_falls_back_to_reach_then_views(self):
        assert compute_engagement_rate({"likes": 10, "reach": 500}) == 2.0
        assert compute_engagement_rate({"likes": 10, "views": 200}) == 5.0

    def test_engagement_rate_none_without_inputs(self):
        assert compute_engagement_rate({"impressions": 100}) is None
        assert compute_engagement_rate({}) is None

    def test_totals_exclude_unsupported_none(self):
        rows = [
            _row(1, "youtube", views=1000, likes=50, comments=5, impressions=None, engagement_rate=5.0),
            _row(2, "youtube", views=2000, likes=10, comments=0, impressions=None, engagement_rate=0.5),
        ]
        summary = analyse_performance(rows, total_published=2)
        assert summary.totals["views"] == 3000
        assert summary.totals["impressions"] is None  # no data → None, not 0
        assert summary.measured_posts == 2
        assert summary.top_posts[0]["content_id"] == 1

    def test_unmeasured_posts_counted_separately(self):
        rows = [_row(1, "twitter"), _row(2, "youtube", views=100, likes=5, engagement_rate=5.0)]
        summary = analyse_performance(rows, total_published=2)
        assert summary.measured_posts == 1
        assert summary.unmeasured_posts == 1


# ----------------------------------------------------------------------
# Feedback + Optimization
# ----------------------------------------------------------------------
class TestFeedback:
    def test_unmeasured_verdict_explains_why(self):
        fb = feedback_for_post(_row(9, "twitter"))
        assert fb.verdict == "unmeasured"
        assert any("official API" in r for r in fb.risks)

    def test_strong_and_attention_thresholds(self):
        assert feedback_for_post(_row(1, "instagram", engagement_rate=6.0, likes=60,
                                       impressions=1000)).verdict == "strong"
        assert feedback_for_post(_row(2, "instagram", engagement_rate=0.2, likes=2,
                                       impressions=1000)).verdict == "needs_attention"

    def test_portfolio_overall_present(self):
        rows = [_row(1, "instagram", engagement_rate=6.0, likes=60, impressions=1000),
                _row(2, "twitter")]
        portfolio = feedback_for_portfolio(rows)
        assert portfolio.per_post and portfolio.overall


class TestOptimizer:
    def test_empty_plan_recommends_measurement_first(self):
        summary = PerformanceSummary(total_published=0, measured_posts=0, unmeasured_posts=0)
        plan = build_optimization_plan(summary)
        assert plan.best_platform is None
        assert any(s.area == "measurement" and s.priority == "high" for s in plan.suggestions)

    def test_best_platform_picked_from_measured_data(self):
        rows = [
            _row(1, "instagram", likes=100, comments=20, impressions=2000, engagement_rate=6.0),
            _row(2, "youtube", views=5000, likes=10, comments=1, engagement_rate=0.22),
        ]
        summary = analyse_performance(rows, total_published=2)
        plan = build_optimization_plan(summary)
        assert plan.best_platform == "instagram"
        assert any(s.area == "platform" for s in plan.suggestions)


# ----------------------------------------------------------------------
# Isolation guard: content analytics must not depend on career analytics
# ----------------------------------------------------------------------
class TestIsolation:
    def test_no_career_imports(self):
        import re

        root = Path(__file__).resolve().parents[2] / "backend" / "content_analytics"
        offenders = []
        for path in root.glob("*.py"):
            for line in path.read_text(encoding="utf-8").splitlines():
                stripped = line.strip()
                if not stripped or stripped.startswith(("#", '"""', "'''", "-", "*", "NEVER", "Career analytics")):
                    continue
                # Only real code imports / table references count as coupling;
                # docstrings explaining the isolation contract are allowed.
                if re.search(r"^\s*(import|from)\s+.*career", line):
                    offenders.append(f"{path.name}: {line.strip()}")
                elif "CareerService" in line and ("import" in line or "career_service" in line):
                    offenders.append(f"{path.name}: {line.strip()}")
        assert offenders == [], f"career coupling found: {offenders}"

    def test_api_router_does_not_import_career(self):
        import re

        root = Path(__file__).resolve().parents[2] / "backend" / "api" / "content_analytics.py"
        code_imports = [line for line in root.read_text(encoding="utf-8").splitlines()
                        if re.match(r"\s*(import|from)\s+", line)]
        assert not any("career" in line.lower() for line in code_imports), \
            f"career import in router: {[l for l in code_imports if 'career' in l.lower()]}"


# ----------------------------------------------------------------------
# Service: DB mapping (unsupported 0 in DB → None in public schema)
# ----------------------------------------------------------------------
class TestServiceMapping:
    def test_to_public_snapshot_restores_none(self, db_session):
        from backend.content_analytics.service import ContentAnalyticsService
        from backend.models import User
        from backend.models.content_calendar import (
            ContentAnalytics, ContentCalendar, ContentStatus, ContentType, SocialPlatform,
        )

        user = User(email="ca@example.com", hashed_password="x", full_name="CA",
                    is_active=True, is_verified=True)
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        item = ContentCalendar(user_id=user.id, title="YT", content="hello",
                               content_type=ContentType.VIDEO, platform=SocialPlatform.YOUTUBE,
                               status=ContentStatus.PUBLISHED, platform_post_id="vid1")
        db_session.add(item)
        db_session.commit()
        db_session.refresh(item)

        # Legacy row: unsupported metrics stored as 0.
        row = ContentAnalytics(content_id=item.id, user_id=user.id, platform=SocialPlatform.YOUTUBE,
                               platform_post_id="vid1", views=1000, likes=50, comments=5,
                               shares=0, saves=0, clicks=0, impressions=0, reach=0,
                               engagement_rate=5.0, click_through_rate=0.0)
        db_session.add(row)
        db_session.commit()
        db_session.refresh(row)

        service = ContentAnalyticsService(db_session)
        snap = service.to_public_snapshot(row)
        assert snap.views == 1000
        assert snap.likes == 50
        # YouTube impressions/shares unsupported → None even though DB holds 0.
        assert snap.impressions is None
        assert snap.shares is None

    def test_list_published_includes_statuses(self, db_session):
        from backend.content_analytics.service import ContentAnalyticsService
        from backend.models import User
        from backend.models.content_calendar import ContentCalendar, ContentStatus, ContentType, SocialPlatform

        user = User(email="ca2@example.com", hashed_password="x", full_name="CA2",
                    is_active=True, is_verified=True)
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        for st in (ContentStatus.PUBLISHED, ContentStatus.FAILED, ContentStatus.DRAFT):
            db_session.add(ContentCalendar(user_id=user.id, title=f"t-{st.value}", content="c",
                                           content_type=ContentType.POST, platform=SocialPlatform.FACEBOOK,
                                           status=st))
        db_session.commit()
        service = ContentAnalyticsService(db_session)
        items = service.list_published(user.id, include_failed=True)
        assert {i.status for i in items} >= {ContentStatus.PUBLISHED, ContentStatus.FAILED}
        assert all(i.status != ContentStatus.DRAFT for i in items)
