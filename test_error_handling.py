from backend.agents.research.error_handling import (
    ErrorHandler, PipelineError, ErrorSeverity, ErrorCategory,
    NetworkError, SourceError, LLMError, ValidationError, TimeoutError,
    EmptyResultsError, DuplicateError, ConflictError, DatabaseError,
    ErrorContext, CircuitBreaker, search_circuit_breaker, llm_circuit_breaker,
    with_error_handling,
)

handler = ErrorHandler()

net_error = NetworkError('Connection timeout')
print(f'NetworkError: category={net_error.category.value}, severity={net_error.severity.value}')

src_error = SourceError('Invalid API key')
print(f'SourceError: category={src_error.category.value}, severity={src_error.severity.value}')

llm_error = LLMError('Rate limit exceeded')
print(f'LLMError: category={llm_error.category.value}, severity={llm_error.severity.value}')

print(f'Categorize connection error: {handler.categorize_error(Exception("connection refused"))}')
print(f'Categorize timeout error: {handler.categorize_error(Exception("request timed out"))}')
print(f'Categorize rate limit error: {handler.categorize_error(Exception("rate limit exceeded"))}')
print(f'Categorize empty results: {handler.categorize_error(Exception("no results found"))}')
print(f'Categorize database error: {handler.categorize_error(Exception("database connection failed"))}')

cb = CircuitBreaker(failure_threshold=3, recovery_timeout=1)
print(f'Circuit breaker initial state: {cb.state}')
cb.on_failure()
cb.on_failure()
print(f'After 2 failures: {cb.state}')
cb.on_failure()
print(f'After 3 failures: {cb.state}')

print('All error handling tests passed!')