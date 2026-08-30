import logging
import asyncio
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
import traceback

from backend.agents.research.pipeline_base import PipelineState, PipelinePhase

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ErrorSeverity(str, Enum):
    LOW = "low"           # Warning, continue
    MEDIUM = "medium"     # Recoverable, retry
    HIGH = "high"         # Phase failure, skip phase
    CRITICAL = "critical" # Pipeline failure, abort


class ErrorCategory(str, Enum):
    NETWORK = "network"
    SOURCE = "source"
    LLM = "llm"
    VALIDATION = "validation"
    TIMEOUT = "timeout"
    EMPTY_RESULTS = "empty_results"
    DUPLICATE = "duplicate"
    CONFLICT = "conflict"
    DATABASE = "database"
    UNKNOWN = "unknown"


class PipelineError(Exception):
    """Base pipeline error with context."""

    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        phase: Optional[str] = None,
        recoverable: bool = True,
        details: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(message)
        self.message = message
        self.category = category
        self.severity = severity
        self.phase = phase
        self.recoverable = recoverable
        self.details = details or {}
        self.original_error = original_error
        self.timestamp = datetime.utcnow()
        self.traceback = traceback.format_exc() if original_error else None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message": self.message,
            "category": self.category.value,
            "severity": self.severity.value,
            "phase": self.phase,
            "recoverable": self.recoverable,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
            "original_error": str(self.original_error) if self.original_error else None,
        }


class NetworkError(PipelineError):
    def __init__(self, message: str, **kwargs):
        super().__init__(message, category=ErrorCategory.NETWORK, **kwargs)


class SourceError(PipelineError):
    def __init__(self, message: str, **kwargs):
        super().__init__(message, category=ErrorCategory.SOURCE, **kwargs)


class LLMError(PipelineError):
    def __init__(self, message: str, **kwargs):
        super().__init__(message, category=ErrorCategory.LLM, **kwargs)


class ValidationError(PipelineError):
    def __init__(self, message: str, **kwargs):
        super().__init__(message, category=ErrorCategory.VALIDATION, **kwargs)


class TimeoutError(PipelineError):
    def __init__(self, message: str, **kwargs):
        super().__init__(message, category=ErrorCategory.TIMEOUT, **kwargs)


class EmptyResultsError(PipelineError):
    def __init__(self, message: str, **kwargs):
        super().__init__(message, category=ErrorCategory.EMPTY_RESULTS, **kwargs)


class DuplicateError(PipelineError):
    def __init__(self, message: str, **kwargs):
        super().__init__(message, category=ErrorCategory.DUPLICATE, **kwargs)


class ConflictError(PipelineError):
    def __init__(self, message: str, **kwargs):
        super().__init__(message, category=ErrorCategory.CONFLICT, **kwargs)


class DatabaseError(PipelineError):
    def __init__(self, message: str, **kwargs):
        super().__init__(message, category=ErrorCategory.DATABASE, **kwargs)


@dataclass
class ErrorContext:
    """Context for error handling."""
    phase: str
    research_id: int
    attempt: int = 1
    max_attempts: int = 3
    errors: List[PipelineError] = field(default_factory=list)
    partial_results: Dict[str, Any] = field(default_factory=dict)


class ErrorHandler:
    """Centralized error handling for pipeline."""

    def __init__(
        self,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        exponential_backoff: bool = True,
    ):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.exponential_backoff = exponential_backoff

    async def handle_error(
        self,
        error: Exception,
        context: ErrorContext,
    ) -> Dict[str, Any]:
        """Handle an error and determine recovery action."""
        # Convert to PipelineError if needed
        if not isinstance(error, PipelineError):
            pipeline_error = PipelineError(
                message=str(error),
                category=ErrorCategory.UNKNOWN,
                original_error=error,
            )
        else:
            pipeline_error = error

        pipeline_error.phase = context.phase
        context.errors.append(pipeline_error)

        logger.error(
            f"Research {context.research_id} Phase {context.phase}: "
            f"{pipeline_error.category.value} - {pipeline_error.message}"
        )

        # Determine recovery action based on severity
        if pipeline_error.severity == ErrorSeverity.LOW:
            return {"action": "continue", "error": pipeline_error.to_dict()}

        elif pipeline_error.severity == ErrorSeverity.MEDIUM:
            if context.attempt < context.max_attempts:
                delay = self.retry_delay * (2 ** (context.attempt - 1) if self.exponential_backoff else 1)
                logger.info(f"Retrying in {delay}s (attempt {context.attempt + 1}/{context.max_attempts})")
                await asyncio.sleep(delay)
                return {"action": "retry", "error": pipeline_error.to_dict()}
            else:
                logger.warning(f"Max retries reached, skipping phase")
                return {"action": "skip_phase", "error": pipeline_error.to_dict()}

        elif pipeline_error.severity == ErrorSeverity.HIGH:
            return {"action": "skip_phase", "error": pipeline_error.to_dict()}

        elif pipeline_error.severity == ErrorSeverity.CRITICAL:
            return {"action": "abort", "error": pipeline_error.to_dict()}

        return {"action": "abort", "error": pipeline_error.to_dict()}

    def categorize_error(self, error: Exception) -> ErrorCategory:
        """Categorize an exception."""
        error_str = str(error).lower()
        
        if any(kw in error_str for kw in ["connection", "timeout", "network", "dns", "unreachable"]):
            return ErrorCategory.NETWORK
        elif any(kw in error_str for kw in ["source", "provider", "api key", "unauthorized", "forbidden"]):
            return ErrorCategory.SOURCE
        elif any(kw in error_str for kw in ["llm", "model", "token", "context length", "rate limit"]):
            return ErrorCategory.LLM
        elif any(kw in error_str for kw in ["validation", "schema", "parse", "json", "format"]):
            return ErrorCategory.VALIDATION
        elif any(kw in error_str for kw in ["timeout", "timed out"]):
            return ErrorCategory.TIMEOUT
        elif any(kw in error_str for kw in ["empty", "no results", "not found"]):
            return ErrorCategory.EMPTY_RESULTS
        elif any(kw in error_str for kw in ["duplicate", "already exists"]):
            return ErrorCategory.DUPLICATE
        elif any(kw in error_str for kw in ["conflict", "contradict"]):
            return ErrorCategory.CONFLICT
        elif any(kw in error_str for kw in ["database", "sql", "transaction", "integrity"]):
            return ErrorCategory.DATABASE
        return ErrorCategory.UNKNOWN

    def determine_severity(self, error: Exception, category: ErrorCategory) -> ErrorSeverity:
        """Determine error severity."""
        if category in [ErrorCategory.NETWORK, ErrorCategory.TIMEOUT]:
            return ErrorSeverity.MEDIUM
        elif category in [ErrorCategory.SOURCE, ErrorCategory.LLM]:
            return ErrorSeverity.MEDIUM
        elif category in [ErrorCategory.VALIDATION]:
            return ErrorSeverity.HIGH
        elif category in [ErrorCategory.EMPTY_RESULTS]:
            return ErrorSeverity.LOW  # Often recoverable by trying other sources
        elif category in [ErrorCategory.DUPLICATE]:
            return ErrorSeverity.LOW
        elif category in [ErrorCategory.CONFLICT]:
            return ErrorSeverity.MEDIUM
        elif category in [ErrorCategory.DATABASE]:
            return ErrorSeverity.CRITICAL
        return ErrorSeverity.MEDIUM


def with_error_handling(
    phase: str,
    error_handler: Optional[ErrorHandler] = None,
    fallback: Optional[Callable] = None,
):
    """Decorator for phase error handling. Works with both instance methods and functions."""
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Handle both instance methods (self, state, db_session) and functions (state, db_session)
            if len(args) >= 2 and hasattr(args[0], '__class__') and not isinstance(args[0], PipelineState):
                # Instance method: (self, state, db_session, ...)
                self_obj = args[0]
                state = args[1]
                db_session = args[2] if len(args) > 2 else kwargs.get('db_session')
                remaining_args = args[3:]
            else:
                # Function: (state, db_session, ...)
                state = args[0]
                db_session = args[1] if len(args) > 1 else kwargs.get('db_session')
                remaining_args = args[2:]
                self_obj = None

            handler = error_handler or ErrorHandler()
            context = ErrorContext(
                phase=phase,
                research_id=state.research_id,
            )

            for attempt in range(1, context.max_attempts + 1):
                context.attempt = attempt
                try:
                    if self_obj is not None:
                        result = await func(self_obj, state, db_session, *remaining_args, **kwargs)
                    else:
                        result = await func(state, db_session, *remaining_args, **kwargs)
                    return result
                except Exception as e:
                    category = handler.categorize_error(e)
                    severity = handler.determine_severity(e, category)
                    
                    pipeline_error = PipelineError(
                        message=str(e),
                        category=category,
                        severity=severity,
                        phase=phase,
                        original_error=e,
                    )
                    
                    action_result = await handler.handle_error(pipeline_error, context)
                    
                    if action_result["action"] == "retry":
                        continue
                    elif action_result["action"] == "skip_phase":
                        logger.warning(f"Skipping phase {phase} due to error")
                        state.warnings.append(f"Phase {phase} skipped: {e}")
                        state.error = str(e)
                        if fallback:
                            try:
                                if self_obj is not None:
                                    return await fallback(self_obj, state, db_session)
                                else:
                                    return await fallback(state, db_session)
                            except Exception as fb_error:
                                logger.error(f"Fallback also failed: {fb_error}")
                        return state
                    elif action_result["action"] == "abort":
                        state.error = str(e)
                        state.phase = PipelinePhase.FAILED
                        return state

            state.error = f"Max retries exceeded for phase {phase}"
            state.phase = PipelinePhase.FAILED
            return state

        return wrapper
    return decorator


class CircuitBreaker:
    """Circuit breaker for external services."""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: type = Exception,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = "closed"  # closed, open, half-open

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Call function with circuit breaker."""
        if self.state == "open":
            if self.last_failure_time and \
               (datetime.utcnow() - self.last_failure_time).total_seconds() > self.recovery_timeout:
                self.state = "half-open"
                logger.info("Circuit breaker entering half-open state")
            else:
                raise PipelineError(
                    "Circuit breaker is open",
                    category=ErrorCategory.NETWORK,
                    severity=ErrorSeverity.HIGH,
                )

        try:
            result = func(*args, **kwargs)
            self.on_success()
            return result
        except self.expected_exception as e:
            self.on_failure()
            raise

    async def acall(self, func: Callable, *args, **kwargs) -> Any:
        """Async call with circuit breaker."""
        if self.state == "open":
            if self.last_failure_time and \
               (datetime.utcnow() - self.last_failure_time).total_seconds() > self.recovery_timeout:
                self.state = "half-open"
                logger.info("Circuit breaker entering half-open state")
            else:
                raise PipelineError(
                    "Circuit breaker is open",
                    category=ErrorCategory.NETWORK,
                    severity=ErrorSeverity.HIGH,
                )

        try:
            result = await func(*args, **kwargs)
            self.on_success()
            return result
        except self.expected_exception as e:
            self.on_failure()
            raise

    def on_success(self):
        self.failure_count = 0
        self.state = "closed"

    def on_failure(self):
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")


# Global circuit breakers for external services
search_circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=30)
llm_circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)
database_circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=30)