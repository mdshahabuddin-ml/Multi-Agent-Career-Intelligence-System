from typing import Dict, List, Any, Optional
from backend.evaluation.base import BaseEvaluator, TestCase, EvaluationResult, EvaluationMetric, MetricType
from datetime import datetime
import re


class ResearchQualityEvaluator:
    """Evaluates research output quality including accuracy, completeness, and citation quality."""

    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.min_sources = self.config.get("min_sources", 3)
        self.min_confidence = self.config.get("min_confidence", 0.7)
        self.require_citations = self.config.get("require_citations", True)

    def evaluate(self, test_case: TestCase, actual_output: Dict) -> Dict:
        """Evaluate research quality."""
        metrics = []

        report = actual_output.get("report", {})
        sources = actual_output.get("sources", [])
        claims = actual_output.get("claims", [])
        verification_results = actual_output.get("verification_results", [])

        # Source count
        source_count = len(sources)
        metrics.append(self._create_metric(
            "source_count", MetricType.COMPLETENESS,
            min(source_count / self.min_sources, 1.0),
            threshold=0.7,
            metadata={"actual": source_count, "expected": self.min_sources}
        ))

        # Citation quality
        if self.require_citations:
            citation_score = self._evaluate_citations(report, sources)
            metrics.append(self._create_metric(
                "citation_quality", MetricType.CITATION_QUALITY,
                citation_score,
                threshold=0.6
            ))

        # Claim verification rate
        if claims and verification_results:
            verified_count = sum(1 for v in verification_results if v.get("status") in ["verified", "likely"])
            verification_rate = verified_count / len(claims) if claims else 0
            metrics.append(self._create_metric(
                "verification_rate", MetricType.FACTUALITY,
                verification_rate,
                threshold=0.7
            ))

        # Confidence score
        confidence = actual_output.get("confidence_score", 0)
        metrics.append(self._create_metric(
            "confidence_score", MetricType.ACCURACY,
            confidence,
            threshold=self.min_confidence
        ))

        # Completeness - check for key sections
        completeness = self._evaluate_completeness(report)
        metrics.append(self._create_metric(
            "completeness", MetricType.COMPLETENESS,
            completeness,
            threshold=0.7
        ))

        # Coherence - check report structure
        coherence = self._evaluate_coherence(report)
        metrics.append(self._create_metric(
            "coherence", MetricType.COHERENCE,
            coherence,
            threshold=0.6
        ))

        # Source diversity
        diversity = self._evaluate_source_diversity(sources)
        metrics.append(self._create_metric(
            "source_diversity", MetricType.RELEVANCE,
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

    def _evaluate_citations(self, report: Dict, sources: List[Dict]) -> float:
        """Evaluate citation quality in report."""
        if not report:
            return 0.0

        content = report.get("content", "") or report.get("executive_summary", "") or ""
        if not content:
            return 0.0

        # Count citations in format [1], [2], etc.
        citation_pattern = r'\[\d+\]'
        citations_found = len(re.findall(citation_pattern, content))

        if not sources:
            return 0.0

        # Score based on citation density and coverage
        expected_citations = min(len(sources), 10)
        if expected_citations == 0:
            return 0.0

        citation_coverage = min(citations_found / expected_citations, 1.0)

        # Check if citations reference actual sources
        citation_ids = [int(c.strip('[]')) for c in re.findall(citation_pattern, content)]
        valid_citations = sum(1 for cid in citation_ids if 1 <= cid <= len(sources))

        validity_score = valid_citations / len(citation_ids) if citation_ids else 0

        return (citation_coverage + validity_score) / 2

    def _evaluate_completeness(self, report: Dict) -> float:
        """Evaluate report completeness."""
        if not report:
            return 0.0

        required_sections = [
            "executive_summary",
            "key_findings",
            "recommendations",
            "methodology",
            "limitations"
        ]

        present_sections = 0
        for section in required_sections:
            if report.get(section) and len(str(report.get(section, ""))) > 50:
                present_sections += 1

        return present_sections / len(required_sections)

    def _evaluate_coherence(self, report: Dict) -> float:
        """Evaluate report coherence and structure."""
        if not report:
            return 0.0

        content = report.get("content", "") or report.get("executive_summary", "") or ""
        if not content:
            return 0.0

        # Basic coherence checks
        sentences = re.split(r'[.!?]+', content)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 10]

        if len(sentences) < 3:
            return 0.3

        # Check for transition words
        transitions = ["however", "therefore", "furthermore", "additionally", "consequently",
                       "moreover", "nevertheless", "in contrast", "similarly", "meanwhile"]
        transition_count = sum(1 for s in sentences for t in transitions if t in s.lower())

        transition_score = min(transition_count / max(len(sentences) * 0.2, 1), 1.0)

        # Check sentence length variation (not all too short or too long)
        lengths = [len(s.split()) for s in sentences]
        avg_length = sum(lengths) / len(lengths)
        length_score = 1.0 if 10 <= avg_length <= 30 else 0.5

        return (transition_score + length_score) / 2

    def _evaluate_source_diversity(self, sources: List[Dict]) -> float:
        """Evaluate source diversity."""
        if not sources:
            return 0.0

        domains = set()
        source_types = set()
        for source in sources:
            url = source.get("url", "")
            if url:
                try:
                    domain = url.split("/")[2]
                    domains.add(domain)
                except:
                    pass
            source_types.add(source.get("source_type", "unknown"))

        # Score based on unique domains and types
        domain_score = min(len(domains) / 5, 1.0)  # Expect at least 5 domains
        type_score = min(len(source_types) / 3, 1.0)  # Expect at least 3 types

        return (domain_score + type_score) / 2

    def _create_metric(self, name: str, metric_type: MetricType, value: float,
                       max_value: float = 1.0, threshold: float = 0.7,
                       unit: str = "", metadata: Dict = None) -> Dict:
        """Helper to create a metric."""
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


class ResearchAccuracyEvaluator:
    """Evaluates factual accuracy of research outputs."""

    def __init__(self, config: Dict = None):
        self.config = config or {}

    def evaluate(self, test_case: TestCase, actual_output: Dict) -> Dict:
        """Evaluate research accuracy against ground truth."""
        metrics = []

        expected = test_case.expected_output or {}
        actual = actual_output

        # Fact checking against ground truth
        if expected.get("ground_truth_facts"):
            accuracy = self._check_facts(actual, expected["ground_truth_facts"])
            metrics.append(self._create_metric(
                "factual_accuracy", MetricType.FACTUALITY,
                accuracy,
                threshold=0.8
            ))

        # Claim verification against expected
        if expected.get("expected_claims"):
            claim_accuracy = self._check_claims(actual, expected["expected_claims"])
            metrics.append(self._create_metric(
                "claim_accuracy", MetricType.FACTUALITY,
                claim_accuracy,
                threshold=0.7
            ))

        passed = all(m.get("passed", False) for m in metrics)
        overall_score = sum(m.get("value", 0) for m in metrics) / len(metrics) if metrics else 0

        return {
            "passed": passed,
            "overall_score": overall_score,
            "metrics": metrics
        }

    def _check_facts(self, actual: Dict, expected_facts: List[Dict]) -> float:
        """Check facts against ground truth."""
        if not expected_facts:
            return 1.0

        report_content = str(actual.get("report", {}))
        correct = 0

        for fact in expected_facts:
            fact_text = fact.get("text", "").lower()
            if fact_text and fact_text in report_content.lower():
                correct += 1

        return correct / len(expected_facts)

    def _check_claims(self, actual: Dict, expected_claims: List[str]) -> float:
        """Check if expected claims are present and verified."""
        if not expected_claims:
            return 1.0

        actual_claims = actual.get("claims", [])
        verification_results = actual.get("verification_results", [])

        verified_claims = set()
        for i, v in enumerate(verification_results):
            if v.get("status") in ["verified", "likely"] and i < len(actual_claims):
                verified_claims.add(actual_claims[i].lower())

        matched = 0
        for expected in expected_claims:
            expected_lower = expected.lower()
            for verified in verified_claims:
                if expected_lower in verified or verified in expected_lower:
                    matched += 1
                    break

        return matched / len(expected_claims)

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