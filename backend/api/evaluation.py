from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field

from backend.api import auth
from backend.database import get_db
from backend.dependencies import get_current_active_user
from backend.models import User
from sqlalchemy.orm import Session

router = APIRouter(prefix="/evaluation", tags=["Evaluation"])


class EvaluationRunRequest(BaseModel):
    """Request to run an evaluation."""
    category: str = Field(..., description="Evaluation category: research, rag, job_matching, resume")
    evaluators: Optional[List[str]] = Field(None, description="Specific evaluators to run")
    test_case_ids: Optional[List[str]] = Field(None, description="Specific test cases to run")
    config: Optional[Dict[str, Any]] = Field(None, description="Evaluator configuration")
    mock_outputs: Optional[Dict[str, Any]] = Field(None, description="Mock outputs for testing")


class EvaluationResultResponse(BaseModel):
    """Response for evaluation results."""
    test_case_id: str
    test_case_name: str
    level: str
    passed: bool
    overall_score: float
    duration_ms: int
    metrics: List[Dict[str, Any]]
    metadata: Dict[str, Any] = {}


class EvaluationReportResponse(BaseModel):
    """Complete evaluation report."""
    suite_name: str
    total_test_cases: int
    passed: int
    failed: int
    pass_rate: float
    avg_score: float
    metrics_summary: Dict[str, Any]
    detailed_results: List[EvaluationResultResponse]


class BenchmarkInfoResponse(BaseModel):
    """Benchmark test case info."""
    test_case_id: str
    name: str
    description: str
    level: str
    tags: List[str]


@router.get("/benchmarks", response_model=List[BenchmarkInfoResponse])
async def list_benchmarks(
    category: Optional[str] = Query(None, description="Filter by category"),
    current_user: User = Depends(get_current_active_user),
):
    """List available benchmark test cases."""
    from backend.evaluation.benchmarks import get_benchmarks, ALL_BENCHMARKS

    if category:
        benchmarks = get_benchmarks(category)
    else:
        benchmarks = []
        for cat_benchmarks in ALL_BENCHMARKS.values():
            benchmarks.extend(cat_benchmarks)

    return [
        BenchmarkInfoResponse(
            test_case_id=b.test_case_id,
            name=b.name,
            description=b.description,
            level=b.level.value,
            tags=b.tags,
        )
        for b in benchmarks
    ]


@router.get("/benchmarks/categories")
async def list_benchmark_categories(
    current_user: User = Depends(get_current_active_user),
):
    """List available benchmark categories."""
    from backend.evaluation.benchmarks import ALL_BENCHMARKS, BENCHMARK_CATEGORIES

    return {
        "categories": list(ALL_BENCHMARKS.keys()),
        "evaluators_per_category": BENCHMARK_CATEGORIES,
    }


@router.get("/evaluators")
async def list_evaluators(
    current_user: User = Depends(get_current_active_user),
):
    """List available evaluators."""
    from backend.evaluation.runner import EVALUATORS

    return {
        "evaluators": list(EVALUATORS.keys()),
        "descriptions": {
            "research_quality": "Evaluates research output quality (completeness, citations, verification)",
            "research_accuracy": "Evaluates factual accuracy against ground truth",
            "rag_generation": "Evaluates RAG generation quality (relevance, faithfulness, hallucination)",
            "answer_relevance": "Evaluates answer relevance to query",
            "job_matching": "Evaluates job matching quality (precision, recall, skill match)",
            "job_search": "Evaluates job search filter compliance and ranking",
            "resume_parsing": "Evaluates resume parsing accuracy (skills, experience, education)",
            "resume_scoring": "Evaluates resume scoring and ATS optimization",
        }
    }


@router.post("/run", response_model=EvaluationReportResponse, status_code=status.HTTP_202_ACCEPTED)
async def run_evaluation(
    request: EvaluationRunRequest,
    current_user: User = Depends(get_current_active_user),
):
    """Run evaluation on benchmark test cases."""
    from backend.evaluation.benchmarks import get_benchmarks, ALL_BENCHMARKS
    from backend.evaluation.runner import EVALUATORS, BENCHMARK_CATEGORIES, EvaluationRunner
    from backend.evaluation.base import EvaluationSuite

    # Validate category
    if request.category not in ALL_BENCHMARKS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid category: {request.category}. Valid: {list(ALL_BENCHMARKS.keys())}"
        )

    # Get benchmarks
    benchmarks = get_benchmarks(request.category)
    if request.test_case_ids:
        benchmarks = [b for b in benchmarks if b.test_case_id in request.test_case_ids]

    if not benchmarks:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No matching test cases found"
        )

    # Determine evaluators
    evaluator_names = request.evaluators or BENCHMARK_CATEGORIES.get(request.category, [])

    # Create suite
    suite = EvaluationSuite(f"{request.category}_evaluation_{current_user.id}")

    for benchmark in benchmarks:
        suite.add_test_case(benchmark)

    for eval_name in evaluator_names:
        evaluator_class = EVALUATORS.get(eval_name)
        if evaluator_class:
            evaluator = evaluator_class(request.config.get(eval_name, {}) if request.config else {})
            suite.add_evaluator(evaluator, eval_name)

    # Get actual outputs
    if request.mock_outputs:
        actual_outputs = request.mock_outputs
    else:
        # Generate mock outputs for now - in production would call actual services
        runner = EvaluationRunner()
        actual_outputs = runner._generate_mock_outputs(benchmarks)

    # Run evaluation
    results = suite.run(actual_outputs)
    report = suite.generate_report(results)

    return EvaluationReportResponse(**report)


@router.post("/run/async", status_code=status.HTTP_202_ACCEPTED)
async def run_evaluation_async(
    request: EvaluationRunRequest,
    current_user: User = Depends(get_current_active_user),
):
    """Run evaluation asynchronously (returns task ID)."""
    # In production, this would queue a Celery task
    # For now, run synchronously and return task info
    import uuid

    task_id = str(uuid.uuid4())

    # TODO: Queue as Celery task
    # from backend.workers.evaluation_worker import run_evaluation_task
    # run_evaluation_task.delay(task_id, request.dict(), current_user.id)

    return {
        "task_id": task_id,
        "status": "queued",
        "message": "Evaluation queued. Check status with GET /evaluation/tasks/{task_id}"
    }


@router.get("/tasks/{task_id}")
async def get_evaluation_task_status(
    task_id: str,
    current_user: User = Depends(get_current_active_user),
):
    """Get status of async evaluation task."""
    # In production, would check Celery task status
    return {
        "task_id": task_id,
        "status": "completed",
        "result": "Available at GET /evaluation/results/{task_id}"
    }


@router.get("/results/{task_id}", response_model=EvaluationReportResponse)
async def get_evaluation_results(
    task_id: str,
    current_user: User = Depends(get_current_active_user),
):
    """Get results of completed evaluation task."""
    # In production, would fetch from database/cache
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Evaluation results not found. Task may still be running."
    )


@router.post("/custom", response_model=EvaluationReportResponse)
async def run_custom_evaluation(
    test_cases: List[Dict[str, Any]],
    evaluators: List[str],
    actual_outputs: Dict[str, Dict[str, Any]],
    config: Optional[Dict[str, Any]] = None,
    current_user: User = Depends(get_current_active_user),
):
    """Run evaluation on custom test cases."""
    from backend.evaluation.runner import EVALUATORS
    from backend.evaluation.base import EvaluationSuite, TestCase, EvaluationLevel

    # Parse custom test cases
    benchmarks = []
    for tc_data in test_cases:
        benchmark = TestCase(
            test_case_id=tc_data["test_case_id"],
            name=tc_data["name"],
            description=tc_data.get("description", ""),
            level=EvaluationLevel(tc_data.get("level", "component")),
            input_data=tc_data.get("input_data", {}),
            expected_output=tc_data.get("expected_output"),
            tags=tc_data.get("tags", []),
        )
        benchmarks.append(benchmark)

    # Create suite
    suite = EvaluationSuite(f"custom_evaluation_{current_user.id}")

    for benchmark in benchmarks:
        suite.add_test_case(benchmark)

    for eval_name in evaluators:
        evaluator_class = EVALUATORS.get(eval_name)
        if evaluator_class:
            evaluator = evaluator_class(config.get(eval_name, {}) if config else {})
            suite.add_evaluator(evaluator, eval_name)

    # Run evaluation
    results = suite.run(actual_outputs)
    report = suite.generate_report(results)

    return EvaluationReportResponse(**report)


@router.get("/history")
async def get_evaluation_history(
    limit: int = Query(50, le=100),
    category: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
):
    """Get evaluation history for current user."""
    # In production, would query database
    return {
        "history": [],
        "message": "Evaluation history not yet implemented. Requires database storage."
    }