from typing import Dict, List, Any, Optional
from backend.evaluation.base import BaseEvaluator, TestCase, EvaluationResult, EvaluationMetric, MetricType
import re


class ResumeParsingEvaluator:
    """Evaluates resume parsing accuracy including skills, experience, and education extraction."""

    def __init__(self, config: Dict = None):
        self.config = config or {}

    def evaluate(self, test_case: TestCase, actual_output: Dict) -> Dict:
        """Evaluate resume parsing quality."""
        metrics = []

        expected = test_case.expected_output or {}
        actual = actual_output

        # Skills extraction accuracy
        if expected.get("skills"):
            skill_accuracy = self._evaluate_skills(expected["skills"], actual.get("skills", []))
            metrics.append(self._create_metric(
                "skill_extraction_accuracy", MetricType.ACCURACY,
                skill_accuracy,
                threshold=0.7
            ))

        # Experience extraction accuracy
        if expected.get("experience"):
            exp_accuracy = self._evaluate_experience(expected["experience"], actual.get("experience", []))
            metrics.append(self._create_metric(
                "experience_extraction_accuracy", MetricType.ACCURACY,
                exp_accuracy,
                threshold=0.6
            ))

        # Education extraction accuracy
        if expected.get("education"):
            edu_accuracy = self._evaluate_education(expected["education"], actual.get("education", []))
            metrics.append(self._create_metric(
                "education_extraction_accuracy", MetricType.ACCURACY,
                edu_accuracy,
                threshold=0.7
            ))

        # Contact info extraction
        if expected.get("contact_info"):
            contact_accuracy = self._evaluate_contact_info(expected["contact_info"], actual.get("contact_info", {}))
            metrics.append(self._create_metric(
                "contact_info_accuracy", MetricType.COMPLETENESS,
                contact_accuracy,
                threshold=0.8
            ))

        # Section detection completeness
        section_completeness = self._evaluate_sections(expected.get("sections", {}), actual.get("sections", {}))
        metrics.append(self._create_metric(
            "section_detection_completeness", MetricType.COMPLETENESS,
            section_completeness,
            threshold=0.7
        ))

        # Overall parsing quality
        parsing_quality = self._evaluate_parsing_quality(actual)
        metrics.append(self._create_metric(
            "parsing_quality", MetricType.USEFULNESS,
            parsing_quality,
            threshold=0.6
        ))

        passed = all(m.get("passed", False) for m in metrics)
        overall_score = sum(m.get("value", 0) for m in metrics) / len(metrics) if metrics else 0

        return {
            "passed": passed,
            "overall_score": overall_score,
            "metrics": metrics
        }

    def _evaluate_skills(self, expected_skills: List[str], actual_skills: List[str]) -> float:
        """Evaluate skill extraction using fuzzy matching."""
        if not expected_skills:
            return 1.0 if not actual_skills else 0.5

        if not actual_skills:
            return 0.0

        expected_lower = [s.lower().strip() for s in expected_skills]
        actual_lower = [s.lower().strip() for s in actual_skills]

        matched = 0
        for exp in expected_lower:
            for act in actual_lower:
                if self._skills_match(exp, act):
                    matched += 1
                    break

        return matched / len(expected_skills)

    def _skills_match(self, skill1: str, skill2: str) -> bool:
        """Check if two skills match (exact or fuzzy)."""
        if skill1 == skill2:
            return True

        # Check if one contains the other
        if skill1 in skill2 or skill2 in skill1:
            return True

        # Check common abbreviations
        abbreviations = {
            "js": "javascript",
            "ts": "typescript",
            "py": "python",
            "ml": "machine learning",
            "ai": "artificial intelligence",
            "dl": "deep learning",
            "nlp": "natural language processing",
            "cv": "computer vision",
            "db": "database",
            "api": "application programming interface",
            "ui": "user interface",
            "ux": "user experience",
            "ci": "continuous integration",
            "cd": "continuous deployment",
            "devops": "development operations",
            "k8s": "kubernetes",
            "aws": "amazon web services",
            "gcp": "google cloud platform",
        }

        for abbr, full in abbreviations.items():
            if (skill1 == abbr and skill2 == full) or (skill1 == full and skill2 == abbr):
                return True

        return False

    def _evaluate_experience(self, expected_exp: List[Dict], actual_exp: List[Dict]) -> float:
        """Evaluate experience extraction."""
        if not expected_exp:
            return 1.0 if not actual_exp else 0.5

        if not actual_exp:
            return 0.0

        total_score = 0.0
        for exp in expected_exp:
            best_match = 0.0
            for act in actual_exp:
                score = self._compare_experience(exp, act)
                best_match = max(best_match, score)
            total_score += best_match

        return total_score / len(expected_exp)

    def _compare_experience(self, exp1: Dict, exp2: Dict) -> float:
        """Compare two experience entries."""
        score = 0.0
        fields = ["title", "company", "location", "description"]
        weights = {"title": 0.3, "company": 0.3, "location": 0.1, "description": 0.3}

        for field in fields:
            val1 = str(exp1.get(field, "")).lower()
            val2 = str(exp2.get(field, "")).lower()

            if not val1:
                continue

            if val1 == val2:
                score += weights[field]
            elif val1 in val2 or val2 in val1:
                score += weights[field] * 0.7
            elif self._partial_match(val1, val2):
                score += weights[field] * 0.4

        return score

    def _partial_match(self, s1: str, s2: str) -> bool:
        """Check for partial word overlap."""
        words1 = set(s1.split())
        words2 = set(s2.split())
        if not words1 or not words2:
            return False
        overlap = len(words1 & words2) / len(words1)
        return overlap > 0.5

    def _evaluate_education(self, expected_edu: List[Dict], actual_edu: List[Dict]) -> float:
        """Evaluate education extraction."""
        if not expected_edu:
            return 1.0 if not actual_edu else 0.5

        if not actual_edu:
            return 0.0

        total_score = 0.0
        for edu in expected_edu:
            best_match = 0.0
            for act in actual_edu:
                score = self._compare_education(edu, act)
                best_match = max(best_match, score)
            total_score += best_match

        return total_score / len(expected_edu)

    def _compare_education(self, edu1: Dict, edu2: Dict) -> float:
        """Compare two education entries."""
        score = 0.0
        fields = ["degree", "institution", "field_of_study", "graduation_year"]
        weights = {"degree": 0.4, "institution": 0.3, "field_of_study": 0.2, "graduation_year": 0.1}

        for field in fields:
            val1 = str(edu1.get(field, "")).lower()
            val2 = str(edu2.get(field, "")).lower()

            if not val1:
                continue

            if val1 == val2:
                score += weights[field]
            elif val1 in val2 or val2 in val1:
                score += weights[field] * 0.7

        return score

    def _evaluate_contact_info(self, expected: Dict, actual: Dict) -> float:
        """Evaluate contact info extraction."""
        fields = ["email", "phone", "linkedin", "github", "website"]
        weights = {"email": 0.4, "phone": 0.2, "linkedin": 0.2, "github": 0.1, "website": 0.1}

        score = 0.0
        for field in fields:
            exp_val = str(expected.get(field, "")).lower()
            act_val = str(actual.get(field, "")).lower()

            if not exp_val:
                continue

            if exp_val == act_val:
                score += weights[field]
            elif exp_val in act_val or act_val in exp_val:
                score += weights[field] * 0.8

        return score

    def _evaluate_sections(self, expected: Dict, actual: Dict) -> float:
        """Evaluate section detection completeness."""
        expected_sections = set(expected.keys())
        actual_sections = set(actual.keys())

        if not expected_sections:
            return 1.0

        found = len(expected_sections & actual_sections)
        return found / len(expected_sections)

    def _evaluate_parsing_quality(self, actual: Dict) -> float:
        """Evaluate overall parsing quality."""
        score = 0.0
        checks = [
            ("has_skills", bool(actual.get("skills"))),
            ("has_experience", bool(actual.get("experience"))),
            ("has_education", bool(actual.get("education"))),
            ("has_contact", bool(actual.get("contact_info"))),
            ("has_sections", bool(actual.get("sections"))),
        ]

        for _, check in checks:
            if check:
                score += 1.0

        return score / len(checks)

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


class ResumeScoringEvaluator:
    """Evaluates resume scoring and ATS optimization."""

    def __init__(self, config: Dict = None):
        self.config = config or {}

    def evaluate(self, test_case: TestCase, actual_output: Dict) -> Dict:
        metrics = []

        expected = test_case.expected_output or {}
        actual = actual_output

        # Score accuracy
        if "ats_score" in expected:
            score_diff = abs(expected["ats_score"] - actual.get("ats_score", 0))
            accuracy = max(0, 1.0 - score_diff / 100)
            metrics.append(self._create_metric(
                "ats_score_accuracy", MetricType.ACCURACY,
                accuracy,
                threshold=0.7
            ))

        # Keyword coverage
        if expected.get("required_keywords"):
            coverage = self._evaluate_keyword_coverage(
                expected["required_keywords"],
                actual.get("matched_keywords", [])
            )
            metrics.append(self._create_metric(
                "keyword_coverage", MetricType.COMPLETENESS,
                coverage,
                threshold=0.6
            ))

        # Recommendation quality
        if expected.get("expected_recommendations"):
            rec_quality = self._evaluate_recommendations(
                expected["expected_recommendations"],
                actual.get("recommendations", [])
            )
            metrics.append(self._create_metric(
                "recommendation_quality", MetricType.USEFULNESS,
                rec_quality,
                threshold=0.5
            ))

        passed = all(m.get("passed", False) for m in metrics)
        overall_score = sum(m.get("value", 0) for m in metrics) / len(metrics) if metrics else 0

        return {
            "passed": passed,
            "overall_score": overall_score,
            "metrics": metrics
        }

    def _evaluate_keyword_coverage(self, required: List[str], matched: List[str]) -> float:
        if not required:
            return 1.0
        required_lower = set(r.lower() for r in required)
        matched_lower = set(m.lower() for m in matched)
        return len(required_lower & matched_lower) / len(required_lower)

    def _evaluate_recommendations(self, expected: List[str], actual: List[str]) -> float:
        if not expected:
            return 1.0 if not actual else 0.5

        expected_lower = set(e.lower() for e in expected)
        actual_lower = set(a.lower() for a in actual)
        return len(expected_lower & actual_lower) / len(expected_lower)

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