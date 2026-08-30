#!/usr/bin/env python
"""Evaluation Runner CLI for CareerIntel AI."""

import argparse
import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.evaluation.base import EvaluationSuite, TestCase, EvaluationLevel
from backend.evaluation.research import ResearchQualityEvaluator, ResearchAccuracyEvaluator
from backend.evaluation.generation import RAGGenerationEvaluator, AnswerRelevanceEvaluator
from backend.evaluation.job_matching import JobMatchingEvaluator, JobSearchEvaluator
from backend.evaluation.resume import ResumeParsingEvaluator, ResumeScoringEvaluator
from backend.evaluation.benchmarks import get_benchmarks, ALL_BENCHMARKS


EVALUATORS = {
    "research_quality": ResearchQualityEvaluator,
    "research_accuracy": ResearchAccuracyEvaluator,
    "rag_generation": RAGGenerationEvaluator,
    "answer_relevance": AnswerRelevanceEvaluator,
    "job_matching": JobMatchingEvaluator,
    "job_search": JobSearchEvaluator,
    "resume_parsing": ResumeParsingEvaluator,
    "resume_scoring": ResumeScoringEvaluator,
}


BENCHMARK_CATEGORIES = {
    "research": ["research_quality", "research_accuracy"],
    "rag": ["rag_generation", "answer_relevance"],
    "job_matching": ["job_matching", "job_search"],
    "resume": ["resume_parsing", "resume_scoring"],
}


class EvaluationRunner:
    """Runs evaluations against benchmark test cases."""

    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.results = []

    def run_category(self, category: str, evaluator_names: List[str] = None,
                     mock_outputs: Dict = None) -> Dict:
        """Run evaluation for a specific category."""
        benchmarks = get_benchmarks(category)
        if not benchmarks:
            return {"error": f"No benchmarks found for category: {category}"}

        if not evaluator_names:
            evaluator_names = BENCHMARK_CATEGORIES.get(category, [])

        suite = EvaluationSuite(f"{category}_evaluation")

        for benchmark in benchmarks:
            suite.add_test_case(benchmark)

        # Get unique levels from benchmarks
        levels = set(b.level.value for b in benchmarks)

        for eval_name in evaluator_names:
            evaluator_class = EVALUATORS.get(eval_name)
            if evaluator_class:
                evaluator = evaluator_class(self.config.get(eval_name, {}))
                # Register evaluator for each level in this category
                for level in levels:
                    suite.add_evaluator(evaluator, level)

        if mock_outputs:
            actual_outputs = mock_outputs
        else:
            actual_outputs = self._generate_mock_outputs(benchmarks)

        results = suite.run(actual_outputs)
        report = suite.generate_report(results)

        self.results.append({
            "category": category,
            "timestamp": datetime.utcnow().isoformat(),
            "report": report,
        })

        return report

    def run_all(self, mock_outputs: Dict = None) -> Dict:
        """Run all evaluation categories."""
        all_results = {}
        for category in ALL_BENCHMARKS.keys():
            print(f"Running {category} evaluations...")
            result = self.run_category(category, mock_outputs=mock_outputs.get(category) if mock_outputs else None)
            all_results[category] = result
        return all_results

    def _generate_mock_outputs(self, benchmarks: List[TestCase]) -> Dict[str, Dict]:
        """Generate mock outputs for testing the evaluation framework."""
        outputs = {}
        for benchmark in benchmarks:
            tc_id = benchmark.test_case_id

            if "research" in tc_id:
                outputs[tc_id] = {
                    "report": {
                        "executive_summary": "Test summary",
                        "key_findings": ["Finding 1", "Finding 2"],
                        "recommendations": ["Rec 1", "Rec 2"],
                        "methodology": "Test methodology",
                        "limitations": "Test limitations",
                        "content": "Test report content with [1] citation.",
                    },
                    "sources": [
                        {"id": "1", "title": "Source 1", "url": "https://example.com/1", "source_type": "web"},
                        {"id": "2", "title": "Source 2", "url": "https://example.com/2", "source_type": "web"},
                    ],
                    "claims": ["Claim 1", "Claim 2"],
                    "verification_results": [
                        {"status": "verified"},
                        {"status": "likely"},
                    ],
                    "confidence_score": 0.85,
                }
            elif "rag" in tc_id:
                outputs[tc_id] = {
                    "generated_answer": "This is a test answer that addresses the query with relevant information [1]. It cites sources properly and is faithful to the retrieved documents.",
                    "retrieved_documents": [
                        {"id": "1", "content": "Test document content", "url": "https://example.com/1"},
                    ],
                }
            elif "job_match" in tc_id or "job_search" in tc_id:
                outputs[tc_id] = {
                    "matched_jobs": [
                        {"id": "job_001", "required_skills": ["Python", "React"], "location": "San Francisco", "is_remote": True, "salary_min": 130000, "salary_max": 180000, "company": "TechCorp", "job_type": "full-time"},
                        {"id": "job_002", "required_skills": ["Python", "Django"], "location": "Remote", "is_remote": True, "salary_min": 140000, "salary_max": 190000, "company": "StartupXYZ", "job_type": "full-time"},
                    ],
                    "jobs": [
                        {"id": "job_001", "is_remote": True, "location": "San Francisco", "job_type": "full-time", "salary_max": 180000},
                    ],
                }
            elif "resume" in tc_id:
                outputs[tc_id] = {
                    "skills": ["Python", "JavaScript", "React", "Node.js", "PostgreSQL", "Docker", "AWS"],
                    "experience": [
                        {"title": "Software Engineer", "company": "TechCorp", "location": "San Francisco", "description": "Built scalable applications"},
                    ],
                    "education": [
                        {"degree": "BS Computer Science", "institution": "Stanford", "field_of_study": "CS", "graduation_year": "2020"},
                    ],
                    "contact_info": {"email": "test@example.com", "linkedin": "linkedin.com/in/test"},
                    "sections": {"experience": True, "education": True, "skills": True, "contact": True},
                    "ats_score": 85,
                    "matched_keywords": ["Python", "React", "AWS"],
                    "recommendations": ["Add more keywords", "Quantify achievements"],
                }
            else:
                outputs[tc_id] = {}

        return outputs

    def print_report(self, report: Dict):
        """Print evaluation report to console."""
        print(f"\n{'='*60}")
        print(f"Evaluation Report: {report['suite_name']}")
        print(f"{'='*60}")
        print(f"Total Test Cases: {report['total_test_cases']}")
        print(f"Passed: {report['passed']}")
        print(f"Failed: {report['failed']}")
        print(f"Pass Rate: {report['pass_rate']:.1%}")
        print(f"Average Score: {report['avg_score']:.3f}")
        print(f"\nMetrics Summary:")
        for metric_name, summary in report['metrics_summary'].items():
            status = "PASS" if summary['pass_rate'] >= 0.7 else "FAIL"
            print(f"  {metric_name}: {summary['avg_value']:.3f} (pass rate: {summary['pass_rate']:.1%}) [{status}]")

        print(f"\nDetailed Results:")
        for result in report['detailed_results']:
            status = "PASS" if result['passed'] else "FAIL"
            print(f"  {result['test_case_name']}: {status} (score: {result['overall_score']:.3f})")
            for metric in result['metrics']:
                m_status = "PASS" if metric['passed'] else "FAIL"
                print(f"    {metric['name']}: {metric['value']:.3f} [{m_status}]")


def main():
    parser = argparse.ArgumentParser(description="CareerIntel AI Evaluation Runner")
    parser.add_argument("category", nargs="?", choices=list(ALL_BENCHMARKS.keys()) + ["all"],
                        default="all", help="Evaluation category to run")
    parser.add_argument("--evaluators", nargs="+", choices=list(EVALUATORS.keys()),
                        help="Specific evaluators to run")
    parser.add_argument("--config", type=str, help="Path to config JSON file")
    parser.add_argument("--output", type=str, help="Output file for results (JSON)")
    parser.add_argument("--mock", action="store_true", help="Use mock outputs for testing")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    config = {}
    if args.config:
        with open(args.config) as f:
            config = json.load(f)

    runner = EvaluationRunner(config)

    if args.mock:
        mock_outputs = {}
        for category in ALL_BENCHMARKS.keys():
            benchmarks = get_benchmarks(category)
            mock_outputs[category] = runner._generate_mock_outputs(benchmarks)
    else:
        mock_outputs = None

    if args.category == "all":
        print("Running all evaluation categories...")
        results = runner.run_all(mock_outputs)
        for category, report in results.items():
            if "error" not in report:
                runner.print_report(report)
    else:
        report = runner.run_category(args.category, args.evaluators, mock_outputs)
        if "error" in report:
            print(f"Error: {report['error']}")
            sys.exit(1)
        runner.print_report(report)

    if args.output:
        with open(args.output, 'w') as f:
            json.dump(runner.results, f, indent=2, default=str)
        print(f"\nResults saved to {args.output}")


if __name__ == "__main__":
    main()