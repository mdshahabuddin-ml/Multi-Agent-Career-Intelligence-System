import logging
from typing import Any, Dict, List, Optional

from backend.providers.search.base import (
    SearchProvider, SearchProviderType, SearchConfig, SearchResult
)

logger = logging.getLogger(__name__)


class MockSearchProvider(SearchProvider):
    """Mock search provider for testing."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        results: Optional[List[SearchResult]] = None,
        **kwargs
    ):
        super().__init__(api_key=api_key, base_url=base_url, **kwargs)
        self._results = results or []
        self.call_count = 0

    @property
    def provider_type(self) -> SearchProviderType:
        return SearchProviderType.MOCK

    async def search(self, config: SearchConfig) -> List[SearchResult]:
        self.call_count += 1

        if self._results:
            return self._results[:config.limit]

        # Generate mock results based on query
        mock_results = []
        for i in range(min(config.limit, 5)):
            result = SearchResult(
                url=f"https://example.com/result-{i}",
                title=f"Mock Result {i+1} for: {config.query}",
                snippet=f"This is a mock search result #{i+1} for query '{config.query}'. It contains relevant information about the topic.",
                source_type=config.source_type,
                credibility=0.7,
                relevance=0.8,
                metadata={"mock": True, "index": i}
            )
            mock_results.append(result)

        return mock_results

    async def close(self) -> None:
        pass

    def set_results(self, results: List[SearchResult]) -> None:
        self._results = results

    def add_result(self, result: SearchResult) -> None:
        self._results.append(result)