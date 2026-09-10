"""
Tests for content quality.
"""

import pytest
from backend.content_engine.quality.fact_checker import FactChecker
from backend.content_engine.quality.policy_checker import PolicyChecker
from backend.content_engine.quality.quality_scorer import QualityScorer


class TestFactChecker:
    @pytest.mark.asyncio
    async def test_check(self):
        checker = FactChecker()
        result = await checker.check("Test content")
        assert result["accurate"] is True


class TestPolicyChecker:
    def test_check(self):
        checker = PolicyChecker()
        result = checker.check("Test content")
        assert result["compliant"] is True


class TestQualityScorer:
    def test_score(self):
        scorer = QualityScorer()
        result = scorer.score("Test content")
        assert "score" in result
        assert result["score"] > 0
