from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum
import json


class MetricType(Enum):
    """Types of evaluation metrics."""
    ACCURACY = "accuracy"
    RELEVANCE = "relevance"
    COMPLETENESS = "completeness"
    CONSISTENCY = "consistency"
    FACTUALITY = "factuality"
    CITATION_QUALITY = "citation_quality"
    COHERENCE = "coherence"
    USEFULNESS = "usefulness"
    LATENCY = "latency"
    COST = "cost"


class EvaluationLevel(Enum):
    """Evaluation granularity levels."""
    COMPONENT = "component"      # Individual agent/component
    WORKFLOW = "workflow"        # Multi-agent workflow
    END_TO_END = "end_to_end"    # Full user journey


@dataclass
class EvaluationMetric:
    """A single evaluation metric result."""
    name: str
    metric_type: MetricType
    value: float
    max_value: float = 1.0
    threshold: float = 0.7
    unit: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def passed(self) -> bool:
        return self.value >= self.threshold
    
    @property
    def percentage(self) -> float:
        return (self.value / self.max_value) * 100 if self.max_value > 0 else 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.metric_type.value,
            "value": self.value,
            "max_value": self.max_value,
            "threshold": self.threshold,
            "passed": self.passed,
            "percentage": self.percentage,
            "unit": self.unit,
            "metadata": self.metadata
        }


@dataclass
class EvaluationResult:
    """Complete evaluation result for a test case."""
    test_case_id: str
    test_case_name: str
    level: EvaluationLevel
    metrics: List[EvaluationMetric]
    passed: bool
    overall_score: float
    duration_ms: int
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def passed_metrics(self) -> int:
        return sum(1 for m in self.metrics if m.passed)
    
    @property
    def total_metrics(self) -> int:
        return len(self.metrics)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_case_id": self.test_case_id,
            "test_case_name": self.test_case_name,
            "level": self.level.value,
            "passed": self.passed,
            "overall_score": self.overall_score,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp.isoformat(),
            "metrics": [m.to_dict() for m in self.metrics],
            "metadata": self.metadata
        }


@dataclass
class TestCase:
    """A test case for evaluation."""
    test_case_id: str
    name: str
    description: str
    level: EvaluationLevel
    input_data: Dict[str, Any]
    expected_output: Optional[Dict[str, Any]] = None
    evaluation_criteria: List[Dict[str, Any]] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_case_id": self.test_case_id,
            "name": self.name,
            "description": self.description,
            "level": self.level.value,
            "input_data": self.input_data,
            "expected_output": self.expected_output,
            "evaluation_criteria": self.evaluation_criteria,
            "tags": self.tags,
            "metadata": self.metadata
        }


class BaseEvaluator(ABC):
    """Abstract base class for all evaluators."""
    
    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        self.name = name
        self.config = config or {}
        self.metrics_config = self.config.get("metrics", {})
    
    @abstractmethod
    def evaluate(self, test_case: TestCase, actual_output: Dict[str, Any]) -> EvaluationResult:
        """Evaluate a single test case."""
        pass
    
    def _create_metric(self, name: str, metric_type: MetricType, value: float, 
                       max_value: float = 1.0, threshold: float = 0.7,
                       unit: str = "", metadata: Dict = None) -> EvaluationMetric:
        """Helper to create a metric."""
        return EvaluationMetric(
            name=name,
            metric_type=metric_type,
            value=value,
            max_value=max_value,
            threshold=threshold,
            unit=unit,
            metadata=metadata or {}
        )
    
    def _calculate_overall_score(self, metrics: List[EvaluationMetric]) -> float:
        """Calculate overall score from metrics."""
        if not metrics:
            return 0.0
        total_weight = sum(m.max_value for m in metrics)
        weighted_sum = sum(m.value for m in metrics)
        return weighted_sum / total_weight if total_weight > 0 else 0.0


class EvaluationSuite:
    """Manages a collection of test cases and evaluators."""
    
    def __init__(self, name: str):
        self.name = name
        self.test_cases: List[TestCase] = []
        self.evaluators: Dict[str, BaseEvaluator] = {}
    
    def add_test_case(self, test_case: TestCase):
        """Add a test case to the suite."""
        self.test_cases.append(test_case)
    
    def add_evaluator(self, evaluator: BaseEvaluator, component: str):
        """Register an evaluator for a component."""
        self.evaluators[component] = evaluator
    
    def run(self, actual_outputs: Dict[str, Dict[str, Any]]) -> List[EvaluationResult]:
        """Run all test cases with their evaluators."""
        results = []
        for test_case in self.test_cases:
            evaluator = self.evaluators.get(test_case.level.value)
            if not evaluator:
                # Try to find evaluator by name
                evaluator = self.evaluators.get(test_case.name)
            
            if not evaluator:
                raise ValueError(f"No evaluator found for test case: {test_case.test_case_id}")
            
            actual_output = actual_outputs.get(test_case.test_case_id, {})
            result = evaluator.evaluate(test_case, actual_output)
            
            # Convert dict result to EvaluationResult if needed
            if isinstance(result, dict):
                result = self._convert_dict_to_result(test_case, result)
            
            results.append(result)
        
        return results

    def _convert_dict_to_result(self, test_case: TestCase, result_dict: Dict) -> EvaluationResult:
        """Convert dict result to EvaluationResult."""
        metrics = []
        for m in result_dict.get("metrics", []):
            metrics.append(EvaluationMetric(
                name=m["name"],
                metric_type=MetricType(m["type"]),
                value=m["value"],
                max_value=m.get("max_value", 1.0),
                threshold=m.get("threshold", 0.7),
                unit=m.get("unit", ""),
                metadata=m.get("metadata", {}),
            ))
        
        return EvaluationResult(
            test_case_id=test_case.test_case_id,
            test_case_name=test_case.name,
            level=test_case.level,
            metrics=metrics,
            passed=result_dict.get("passed", False),
            overall_score=result_dict.get("overall_score", 0.0),
            duration_ms=result_dict.get("duration_ms", 0),
        )
    
    def generate_report(self, results: List[EvaluationResult]) -> Dict[str, Any]:
        """Generate a summary report from evaluation results."""
        total = len(results)
        passed = sum(1 for r in results if r.passed)
        
        # Aggregate metrics
        all_metrics = []
        for r in results:
            all_metrics.extend(r.metrics)
        
        metric_summary = {}
        for metric in all_metrics:
            if metric.name not in metric_summary:
                metric_summary[metric.name] = {
                    "total": 0,
                    "passed": 0,
                    "total_value": 0.0,
                    "count": 0
                }
            metric_summary[metric.name]["total"] += 1
            metric_summary[metric.name]["passed"] += 1 if metric.passed else 0
            metric_summary[metric.name]["total_value"] += metric.value
            metric_summary[metric.name]["count"] += 1
        
        return {
            "suite_name": self.name,
            "total_test_cases": total,
            "passed": passed,
            "failed": total - passed,
            "pass_rate": passed / total if total > 0 else 0,
            "avg_score": sum(r.overall_score for r in results) / len(results) if results else 0,
            "metrics_summary": {
                name: {
                    "pass_rate": s["passed"] / s["total"] if s["total"] > 0 else 0,
                    "avg_value": s["total_value"] / s["count"] if s["count"] > 0 else 0,
                }
                for name, s in metric_summary.items()
            },
            "detailed_results": [r.to_dict() for r in results]
        }