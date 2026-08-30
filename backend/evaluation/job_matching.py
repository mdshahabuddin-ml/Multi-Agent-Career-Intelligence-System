from typing import Dict, List, Any, Optional
from backend.evaluation.base import BaseEvaluator, TestCase, EvaluationResult, EvaluationMetric, MetricType
from collections import Counter
import re


class JobMatchingEvaluator:
    """Evaluates job matching quality including relevance, ranking, and recommendation accuracy."""

    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.top_k = self.config.get("top_k", [1, 3, 5, 10])
        self.min_relevance = self.config.get("min_relevance", 0.6)

    def evaluate(self, test_case: TestCase, actual_output: Dict) -> Dict:
        """Evaluate job matching quality."""
        metrics = []

        query = test_case.input_data.get("query", "")
        user_profile = test_case.input_data.get("user_profile", {})
        matched_jobs = actual_output.get("matched_jobs", [])
        expected_jobs = test_case.expected_output.get("relevant_jobs", []) if test_case.expected_output else []

        # Precision@K
        for k in self.top_k:
            if expected_jobs:
                precision = self._precision_at_k(matched_jobs, expected_jobs, k)
                metrics.append(self._create_metric(
                    f"precision@{k}", MetricType.RELEVANCE,
                    precision,
                    threshold=0.5
                ))

        # Recall@K
        for k in self.top_k:
            if expected_jobs:
                recall = self._recall_at_k(matched_jobs, expected_jobs, k)
                metrics.append(self._create_metric(
                    f"recall@{k}", MetricType.COMPLETENESS,
                    recall,
                    threshold=0.5
                ))

        # MRR (Mean Reciprocal Rank)
        if expected_jobs:
            mrr = self._mean_reciprocal_rank(matched_jobs, expected_jobs)
            metrics.append(self._create_metric(
                "mrr", MetricType.RELEVANCE,
                mrr,
                threshold=0.5
            ))

        # NDCG
        if expected_jobs:
            ndcg = self._ndcg_at_k(matched_jobs, expected_jobs, 10)
            metrics.append(self._create_metric(
                "ndcg@10", MetricType.RELEVANCE,
                ndcg,
                threshold=0.5
            ))

        # Skill match quality
        skill_match = self._evaluate_skill_match(user_profile, matched_jobs)
        metrics.append(self._create_metric(
            "skill_match_quality", MetricType.ACCURACY,
            skill_match,
            threshold=self.min_relevance
        ))

        # Location/remote preference match
        location_match = self._evaluate_location_match(user_profile, matched_jobs)
        metrics.append(self._create_metric(
            "location_match", MetricType.RELEVANCE,
            location_match,
            threshold=0.7
        ))

        # Salary expectation match
        salary_match = self._evaluate_salary_match(user_profile, matched_jobs)
        metrics.append(self._create_metric(
            "salary_match", MetricType.RELEVANCE,
            salary_match,
            threshold=0.5
        ))

        # Diversity of recommendations
        diversity = self._evaluate_diversity(matched_jobs)
        metrics.append(self._create_metric(
            "recommendation_diversity", MetricType.USEFULNESS,
            diversity,
            threshold=0.5
        ))

        passed = all(m.get("passed", False) for m in metrics)
        overall_score = sum(m.get("value", 0) for m in metrics) / len(metrics) if metrics else 0

        return {
            "passed": passed,
            "overall_score": overall_score,
            "metrics": metrics
        }

    def _precision_at_k(self, matched: List[Dict], expected: List[str], k: int) -> float:
        if k == 0 or not matched:
            return 0.0
        matched_ids = [job.get("id") or job.get("external_id") for job in matched[:k]]
        expected_set = set(expected)
        hits = sum(1 for mid in matched_ids if mid in expected_set)
        return hits / k

    def _recall_at_k(self, matched: List[Dict], expected: List[str], k: int) -> float:
        if not expected or not matched:
            return 0.0
        matched_ids = [job.get("id") or job.get("external_id") for job in matched[:k]]
        expected_set = set(expected)
        hits = sum(1 for mid in matched_ids if mid in expected_set)
        return hits / len(expected)

    def _mean_reciprocal_rank(self, matched: List[Dict], expected: List[str]) -> float:
        expected_set = set(expected)
        for i, job in enumerate(matched):
            job_id = job.get("id") or job.get("external_id")
            if job_id in expected_set:
                return 1.0 / (i + 1)
        return 0.0

    def _ndcg_at_k(self, matched: List[Dict], expected: List[str], k: int) -> float:
        expected_set = set(expected)
        dcg = 0.0
        for i, job in enumerate(matched[:k]):
            job_id = job.get("id") or job.get("external_id")
            if job_id in expected_set:
                dcg += 1.0 / (i + 1)
        idcg = sum(1.0 / (i + 1) for i in range(min(len(expected), len(matched))))
        return dcg / idcg if idcg > 0 else 0.0

    def _evaluate_skill_match(self, user_profile: Dict, matched_jobs: List[Dict]) -> float:
        """Evaluate how well matched jobs align with user skills."""
        if not matched_jobs:
            return 0.0

        user_skills = set(s.lower() for s in user_profile.get("skills", []))
        if not user_skills:
            return 0.5

        total_score = 0.0
        for job in matched_jobs:
            job_skills = set(s.lower() for s in job.get("required_skills", []))
            if not job_skills:
                continue
            overlap = len(user_skills & job_skills)
            total_score += overlap / len(job_skills)

        return total_score / len(matched_jobs)

    def _evaluate_location_match(self, user_profile: Dict, matched_jobs: List[Dict]) -> float:
        """Evaluate location/remote preference matching."""
        if not matched_jobs:
            return 0.0

        user_location = user_profile.get("preferred_location", "").lower()
        user_remote = user_profile.get("prefers_remote", False)

        matches = 0
        for job in matched_jobs:
            job_location = job.get("location", "").lower()
            job_remote = job.get("is_remote", False)

            if user_remote and job_remote:
                matches += 1
            elif user_location and user_location in job_location:
                matches += 1
            elif not user_location and not user_remote:
                matches += 0.5  # Neutral

        return matches / len(matched_jobs)

    def _evaluate_salary_match(self, user_profile: Dict, matched_jobs: List[Dict]) -> float:
        """Evaluate salary expectation matching."""
        if not matched_jobs:
            return 0.0

        user_min_salary = user_profile.get("min_salary")
        if not user_min_salary:
            return 0.5  # No preference

        matches = 0
        for job in matched_jobs:
            job_min = job.get("salary_min")
            job_max = job.get("salary_max")

            if job_max and job_max >= user_min_salary:
                matches += 1
            elif job_min and job_min >= user_min_salary:
                matches += 0.8

        return matches / len(matched_jobs)

    def _evaluate_diversity(self, matched_jobs: List[Dict]) -> float:
        """Evaluate diversity of job recommendations."""
        if not matched_jobs:
            return 0.0

        companies = set()
        locations = set()
        job_types = set()

        for job in matched_jobs:
            companies.add(job.get("company", ""))
            locations.add(job.get("location", ""))
            job_types.add(job.get("job_type", ""))

        # Normalize by expected diversity
        company_diversity = min(len(companies) / 5, 1.0)
        location_diversity = min(len(locations) / 3, 1.0)
        type_diversity = min(len(job_types) / 3, 1.0)

        return (company_diversity + location_diversity + type_diversity) / 3

    def _create_metric(self, name: str, metric_type: MetricType, value: float,
                       max_value: float = 1.0, threshold: float = 0.7,
                       unit: str = "", metadata: Dict = None) -> Dict:
        return {
            "name": name,
            "type": metric_type.value,
            "value": value,
            "max_value": max_value,
            "threshold": threshold,
            "passed": value >= threshold,
            "percentage": (value / max_value) * 100 if max_value > 0 else 0,
            "unit": unit,
            "metadata": metadata or {}
        }


class JobSearchEvaluator:
    """Evaluates job search functionality."""

    def __init__(self, config: Dict = None):
        self.config = config or {}

    def evaluate(self, test_case: TestCase, actual_output: Dict) -> Dict:
        metrics = []

        query = test_case.input_data.get("query", "")
        filters = test_case.input_data.get("filters", {})
        results = actual_output.get("jobs", [])
        expected = test_case.expected_output.get("expected_jobs", []) if test_case.expected_output else []

        # Filter compliance
        filter_score = self._check_filter_compliance(results, filters)
        metrics.append(self._create_metric(
            "filter_compliance", MetricType.ACCURACY,
            filter_score,
            threshold=0.8
        ))

        # Result ranking quality
        if expected:
            ranking = self._evaluate_ranking(results, expected)
            metrics.append(self._create_metric(
                "ranking_quality", MetricType.RELEVANCE,
                ranking,
                threshold=0.6
            ))

        passed = all(m.get("passed", False) for m in metrics)
        overall_score = sum(m.get("value", 0) for m in metrics) / len(metrics) if metrics else 0

        return {
            "passed": passed,
            "overall_score": overall_score,
            "metrics": metrics
        }

    def _check_filter_compliance(self, results: List[Dict], filters: Dict) -> float:
        if not filters or not results:
            return 1.0

        compliant = 0
        for job in results:
            ok = True
            if filters.get("remote_only") and not job.get("is_remote"):
                ok = False
            if filters.get("location") and filters["location"].lower() not in job.get("location", "").lower():
                ok = False
            if filters.get("job_type") and job.get("job_type") != filters["job_type"]:
                ok = False
            if filters.get("min_salary") and job.get("salary_max", 0) < filters["min_salary"]:
                ok = False
            if ok:
                compliant += 1

        return compliant / len(results)

    def _evaluate_ranking(self, results: List[Dict], expected: List[str]) -> float:
        expected_set = set(expected)
        if not expected_set:
            return 0.5

        # Check if expected jobs appear in top positions
        score = 0.0
        for i, job in enumerate(results):
            job_id = job.get("id") or job.get("external_id")
            if job_id in expected_set:
                score += 1.0 / (i + 1)

        # Normalize
        max_score = sum(1.0 / (i + 1) for i in range(len(expected)))
        return score / max_score if max_score > 0 else 0.0

    def _create_metric(self, name: str, metric_type: MetricType, value: float,
                       max_value: float = 1.0, threshold: float = 0.7,
                       unit: str = "", metadata: Dict = None) -> Dict:
        return {
            "name": name,
            "type": metric_type.value,
            "value": value,
            "max_value": max_value,
            "threshold": threshold,
            "passed": value >= threshold,
            "percentage": (value / max_value) * 100 if max_value > 0 else 0,
            "unit": unit,
            "metadata": metadata or {}
        }