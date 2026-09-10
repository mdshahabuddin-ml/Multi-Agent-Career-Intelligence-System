"""
Tests for Hermes learning module.
"""

import pytest
from backend.hermes_engine.learning.feedback_manager import FeedbackManager
from backend.hermes_engine.learning.performance_analyzer import PerformanceAnalyzer
from backend.hermes_engine.learning.improvement_engine import ImprovementEngine
from backend.hermes_engine.learning.learning_loop import LearningLoop


@pytest.fixture
def feedback_manager():
    return FeedbackManager()


@pytest.fixture
def performance_analyzer():
    return PerformanceAnalyzer()


@pytest.fixture
def improvement_engine():
    return ImprovementEngine()


@pytest.fixture
def learning_loop():
    return LearningLoop()


class TestFeedbackManager:
    def test_submit(self, feedback_manager):
        entry = feedback_manager.submit("agent1", "task1", 5, "Great work")
        assert entry["rating"] == 5

    def test_get_average(self, feedback_manager):
        feedback_manager.submit("agent1", "task1", 4)
        feedback_manager.submit("agent1", "task2", 5)
        avg = feedback_manager.get_average_rating("agent1")
        assert avg == 4.5


class TestPerformanceAnalyzer:
    def test_record(self, performance_analyzer):
        performance_analyzer.record("agent1", "task1", 100.0, True)
        stats = performance_analyzer.get_agent_stats("agent1")
        assert stats["total"] == 1
        assert stats["successful"] == 1


class TestImprovementEngine:
    def test_analyze(self, improvement_engine):
        suggestions = improvement_engine.analyze(
            "agent1",
            {"failed": 5, "total": 10},
            {"average_rating": 2.5},
        )
        assert len(suggestions) > 0


class TestLearningLoop:
    @pytest.mark.asyncio
    async def test_iteration(self, learning_loop):
        result = await learning_loop.run_iteration("agent1", {"score": 0.8})
        assert result["status"] == "completed"
