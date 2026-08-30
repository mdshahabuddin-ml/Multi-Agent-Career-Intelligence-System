import json
import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
import statistics

from backend.evaluation.base import (
    BaseEvaluator, EvaluationSuite, TestCase, EvaluationResult,
    EvaluationMetric, MetricType, EvaluationLevel
)
from backend.evaluation.benchmarks import get_benchmarks, ALL_BENCHMARKS
from backend.evaluation.runner import EvaluationRunner


@dataclass
class BenchmarkRun:
    """A single benchmark run."""
    run_id: str
    timestamp: datetime
    evaluator_name: str
    benchmark_category: str
    results: List[EvaluationResult]
    aggregate_metrics: Dict[str, float]
    passed: bool
    duration_ms: int


@dataclass
class RegressionAlert:
    """Alert for detected regression."""
    metric_name: str
    benchmark_category: str
    current_value: float
    baseline_value: float
    change_percent: float
    threshold_percent: float
    severity: str  # "warning", "critical"
    run_id: str
    timestamp: datetime


class BenchmarkStore:
    """Stores benchmark runs and detects regressions."""
    
    def __init__(self, storage_path: str = "evaluation/benchmarks"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.runs: List[BenchmarkRun] = []
        self.baselines: Dict[str, Dict[str, float]] = {}
        self._load()
    
    def _load(self):
        """Load previous runs from disk."""
        for run_file in self.storage_path.glob("run_*.json"):
            try:
                with open(run_file) as f:
                    data = json.load(f)
                run = BenchmarkRun(
                    run_id=data["run_id"],
                    timestamp=datetime.fromisoformat(data["timestamp"]),
                    evaluator_name=data["evaluator_name"],
                    benchmark_category=data["benchmark_category"],
                    results=[],  # Results not stored for space
                    aggregate_metrics=data["aggregate_metrics"],
                    passed=data["passed"],
                    duration_ms=data["duration_ms"],
                )
                self.runs.append(run)
            except Exception:
                pass
    
    def save_run(self, run: BenchmarkRun):
        """Save a benchmark run."""
        self.runs.append(run)
        
        # Save to disk
        run_file = self.storage_path / f"run_{run.run_id}.json"
        data = {
            "run_id": run.run_id,
            "timestamp": run.timestamp.isoformat(),
            "evaluator_name": run.evaluator_name,
            "benchmark_category": run.benchmark_category,
            "aggregate_metrics": run.aggregate_metrics,
            "passed": run.passed,
            "duration_ms": run.duration_ms,
        }
        with open(run_file, "w") as f:
            json.dump(data, f, indent=2)
        
        # Update baseline if this is the first run or better
        self._update_baseline(run)
    
    def _update_baseline(self, run: BenchmarkRun):
        """Update baseline metrics."""
        key = f"{run.evaluator_name}:{run.benchmark_category}"
        if key not in self.baselines:
            self.baselines[key] = run.aggregate_metrics.copy()
        else:
            # Keep best values as baseline
            for metric, value in run.aggregate_metrics.items():
                if metric not in self.baselines[key] or value > self.baselines[key][metric]:
                    self.baselines[key][metric] = value
        
        # Save baselines
        baseline_file = self.storage_path / "baselines.json"
        with open(baseline_file, "w") as f:
            json.dump(self.baselines, f, indent=2)
    
    def get_baseline(self, evaluator_name: str, benchmark_category: str) -> Optional[Dict[str, float]]:
        """Get baseline for evaluator/category."""
        key = f"{evaluator_name}:{benchmark_category}"
        return self.baselines.get(key)
    
    def get_recent_runs(self, evaluator_name: str, benchmark_category: str, limit: int = 10) -> List[BenchmarkRun]:
        """Get recent runs for trend analysis."""
        filtered = [
            r for r in self.runs
            if r.evaluator_name == evaluator_name and r.benchmark_category == benchmark_category
        ]
        return sorted(filtered, key=lambda r: r.timestamp, reverse=True)[:limit]


class RegressionDetector:
    """Detects regressions in benchmark metrics."""
    
    def __init__(
        self,
        warning_threshold: float = 0.05,
        critical_threshold: float = 0.10,
        min_runs_for_trend: int = 3,
    ):
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
        self.min_runs_for_trend = min_runs_for_trend
    
    def check_regression(
        self,
        current_run: BenchmarkRun,
        baseline: Dict[str, float],
    ) -> List[RegressionAlert]:
        """Check for regressions against baseline."""
        alerts = []
        
        for metric, current_value in current_run.aggregate_metrics.items():
            if metric not in baseline:
                continue
            
            baseline_value = baseline[metric]
            if baseline_value == 0:
                continue
            
            change = (current_value - baseline_value) / baseline_value
            
            if change <= -self.critical_threshold:
                severity = "critical"
            elif change <= -self.warning_threshold:
                severity = "warning"
            else:
                continue
            
            alerts.append(RegressionAlert(
                metric_name=metric,
                benchmark_category=current_run.benchmark_category,
                current_value=current_value,
                baseline_value=baseline_value,
                change_percent=change * 100,
                threshold_percent=(-self.critical_threshold * 100) if severity == "critical" else (-self.warning_threshold * 100),
                severity=severity,
                run_id=current_run.run_id,
                timestamp=current_run.timestamp,
            ))
        
        return alerts
    
    def check_trend(
        self,
        runs: List[BenchmarkRun],
    ) -> List[RegressionAlert]:
        """Check for negative trends over recent runs."""
        if len(runs) < self.min_runs_for_trend:
            return []
        
        alerts = []
        latest = runs[0]
        
        for metric in latest.aggregate_metrics.keys():
            values = [r.aggregate_metrics.get(metric, 0) for r in runs if metric in r.aggregate_metrics]
            if len(values) < self.min_runs_for_trend:
                continue
            
            # Simple linear trend
            x = list(range(len(values)))
            y = values
            
            # Calculate slope
            n = len(values)
            sum_x = sum(x)
            sum_y = sum(y)
            sum_xy = sum(x[i] * y[i] for i in range(n))
            sum_x2 = sum(x[i] * x[i] for i in range(n))
            
            if n * sum_x2 - sum_x * sum_x == 0:
                continue
            
            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
            
            # If slope is significantly negative
            mean_y = statistics.mean(y)
            if mean_y > 0:
                relative_slope = slope / mean_y
                
                if relative_slope <= -0.02:  # 2% decline per run
                    alerts.append(RegressionAlert(
                        metric_name=metric,
                        benchmark_category=latest.benchmark_category,
                        current_value=values[0],
                        baseline_value=mean_y,
                        change_percent=relative_slope * 100,
                        threshold_percent=-2.0,
                        severity="warning",
                        run_id=latest.run_id,
                        timestamp=latest.timestamp,
                    ))
        
        return alerts


class BenchmarkRunner:
    """Orchestrates benchmark runs with regression detection."""
    
    def __init__(
        self,
        runner: EvaluationRunner,
        store: Optional[BenchmarkStore] = None,
        detector: Optional[RegressionDetector] = None,
    ):
        self.runner = runner
        self.store = store or BenchmarkStore()
        self.detector = detector or RegressionDetector()
    
    async def run_benchmark(
        self,
        evaluator: BaseEvaluator,
        benchmark_category: str,
        run_id: Optional[str] = None,
    ) -> BenchmarkRun:
        """Run a full benchmark suite."""
        import uuid
        run_id = run_id or f"{evaluator.name}_{benchmark_category}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        
        start_time = datetime.utcnow()
        
        # Get benchmark test cases
        benchmarks = get_benchmarks(benchmark_category)
        if not benchmarks:
            raise ValueError(f"No benchmarks found for category: {benchmark_category}")
        
        # Create test suite
        suite = EvaluationSuite(f"{evaluator.name}_{benchmark_category}")
        for bm in benchmarks:
            test_case = TestCase(
                test_case_id=bm.get("id", f"{benchmark_category}_{len(suite.test_cases)}"),
                name=bm.get("name", "Unknown"),
                description=bm.get("description", ""),
                level=EvaluationLevel.COMPONENT,
                input_data=bm.get("input", {}),
                expected_output=bm.get("expected", {}),
                evaluation_criteria=bm.get("criteria", []),
            )
            suite.add_test_case(test_case)
        
        # Add evaluator
        suite.add_evaluator(evaluator, evaluator.name)
        
        # Run evaluation
        actual_outputs = {}
        for test_case in suite.test_cases:
            # In real usage, this would call the actual system
            actual_outputs[test_case.test_case_id] = {"mock": "output"}
        
        results = suite.run(actual_outputs)
        
        duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        # Calculate aggregate metrics
        aggregate_metrics = self._calculate_aggregate(results)
        passed = all(r.passed for r in results)
        
        run = BenchmarkRun(
            run_id=run_id,
            timestamp=start_time,
            evaluator_name=evaluator.name,
            benchmark_category=benchmark_category,
            results=results,
            aggregate_metrics=aggregate_metrics,
            passed=passed,
            duration_ms=duration_ms,
        )
        
        # Save and check regressions
        self.store.save_run(run)
        baseline = self.store.get_baseline(evaluator.name, benchmark_category)
        
        regression_alerts = []
        if baseline:
            regression_alerts = self.detector.check_regression(run, baseline)
            trend_alerts = self.detector.check_trend(
                self.store.get_recent_runs(evaluator.name, benchmark_category)
            )
            regression_alerts.extend(trend_alerts)
        
        run.regression_alerts = regression_alerts  # type: ignore
        
        return run
    
    def _calculate_aggregate(self, results: List[EvaluationResult]) -> Dict[str, float]:
        """Calculate aggregate metrics from results."""
        if not results:
            return {}
        
        all_metrics = {}
        for r in results:
            for m in r.metrics:
                if m.name not in all_metrics:
                    all_metrics[m.name] = []
                all_metrics[m.name].append(m.value)
        
        aggregates = {}
        for name, values in all_metrics.items():
            aggregates[f"{name}_mean"] = statistics.mean(values)
            aggregates[f"{name}_median"] = statistics.median(values)
            aggregates[f"{name}_min"] = min(values)
            aggregates[f"{name}_max"] = max(values)
            if len(values) > 1:
                aggregates[f"{name}_stdev"] = statistics.stdev(values)
            aggregates[f"{name}_pass_rate"] = sum(1 for v in values if v >= 0.7) / len(values)
        
        # Overall pass rate
        aggregates["overall_pass_rate"] = sum(1 for r in results if r.passed) / len(results)
        
        return aggregates
    
    async def run_all_benchmarks(self, evaluator: BaseEvaluator) -> List[BenchmarkRun]:
        """Run all benchmark categories for an evaluator."""
        runs = []
        for category in ALL_BENCHMARKS.keys():
            try:
                run = await self.run_benchmark(evaluator, category)
                runs.append(run)
            except Exception as e:
                print(f"Benchmark {category} failed: {e}")
        return runs
    
    def generate_report(self, runs: List[BenchmarkRun]) -> Dict[str, Any]:
        """Generate benchmark report."""
        if not runs:
            return {"error": "No runs to report"}
        
        return {
            "summary": {
                "total_runs": len(runs),
                "passed": sum(1 for r in runs if r.passed),
                "failed": sum(1 for r in runs if not r.passed),
                "total_duration_ms": sum(r.duration_ms for r in runs),
            },
            "by_category": {
                r.benchmark_category: {
                    "passed": r.passed,
                    "duration_ms": r.duration_ms,
                    "metrics": r.aggregate_metrics,
                    "regressions": len(getattr(r, "regression_alerts", [])),
                }
                for r in runs
            },
            "alerts": [
                {
                    "metric": a.metric_name,
                    "category": a.benchmark_category,
                    "current": a.current_value,
                    "baseline": a.baseline_value,
                    "change_pct": a.change_percent,
                    "severity": a.severity,
                }
                for r in runs
                for a in getattr(r, "regression_alerts", [])
            ],
        }


class QualityDashboard:
    """Generates quality dashboard data."""
    
    def __init__(self, store: BenchmarkStore):
        self.store = store
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get data for quality dashboard."""
        if not self.store.runs:
            return {"message": "No benchmark data available"}
        
        latest_runs = {}
        for run in self.store.runs:
            key = f"{run.evaluator_name}:{run.benchmark_category}"
            if key not in latest_runs or run.timestamp > latest_runs[key].timestamp:
                latest_runs[key] = run
        
        return {
            "overview": {
                "total_evaluators": len(set(r.evaluator_name for r in self.store.runs)),
                "total_categories": len(set(r.benchmark_category for r in self.store.runs)),
                "latest_run": max(self.store.runs, key=lambda r: r.timestamp).timestamp.isoformat(),
                "overall_pass_rate": statistics.mean(
                    r.aggregate_metrics.get("overall_pass_rate", 0)
                    for r in latest_runs.values()
                ),
            },
            "evaluators": {
                name: {
                    "categories": list(set(r.benchmark_category for r in self.store.runs if r.evaluator_name == name)),
                    "latest_pass_rate": {
                        cat: latest_runs[f"{name}:{cat}"].aggregate_metrics.get("overall_pass_rate", 0)
                        for cat in set(r.benchmark_category for r in self.store.runs if r.evaluator_name == name)
                    }
                }
                for name in set(r.evaluator_name for r in self.store.runs)
            },
            "metrics_trends": self._get_metric_trends(),
            "regressions": self._get_recent_regressions(),
        }
    
    def _get_metric_trends(self) -> Dict[str, List[Dict]]:
        """Get metric trends over time."""
        trends = {}
        for run in sorted(self.store.runs, key=lambda r: r.timestamp):
            key = f"{run.evaluator_name}:{run.benchmark_category}"
            for metric, value in run.aggregate_metrics.items():
                if metric not in trends:
                    trends[metric] = []
                trends[metric].append({
                    "timestamp": run.timestamp.isoformat(),
                    "value": value,
                    "run_id": run.run_id,
                })
        return trends
    
    def _get_recent_regressions(self, days: int = 30) -> List[Dict]:
        """Get recent regression alerts."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        alerts = []
        for run in self.store.runs:
            if run.timestamp < cutoff:
                continue
            for alert in getattr(run, "regression_alerts", []):
                alerts.append({
                    "metric": alert.metric_name,
                    "category": alert.benchmark_category,
                    "severity": alert.severity,
                    "change_pct": alert.change_percent,
                    "timestamp": alert.timestamp.isoformat(),
                })
        return sorted(alerts, key=lambda a: a["timestamp"], reverse=True)


# Convenience functions
async def run_full_benchmark_suite(
    evaluator: BaseEvaluator,
    store: Optional[BenchmarkStore] = None,
) -> List[BenchmarkRun]:
    """Run complete benchmark suite for evaluator."""
    runner = EvaluationRunner()
    benchmark_runner = BenchmarkRunner(runner, store)
    return await benchmark_runner.run_all_benchmarks(evaluator)


def get_quality_dashboard(store: Optional[BenchmarkStore] = None) -> Dict[str, Any]:
    """Get quality dashboard data."""
    store = store or BenchmarkStore()
    dashboard = QualityDashboard(store)
    return dashboard.get_dashboard_data()