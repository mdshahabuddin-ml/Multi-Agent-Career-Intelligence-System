import logging
from typing import Any, Dict, List, Optional

import httpx

from backend.providers.search.base import (
    SearchProvider, SearchProviderType, SearchConfig, SearchResult
)

logger = logging.getLogger(__name__)


class TavilySearchProvider(SearchProvider):
    """Tavily search provider implementation."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.tavily.com",
        **kwargs
    ):
        super().__init__(api_key=api_key, base_url=base_url, **kwargs)
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def provider_type(self) -> SearchProviderType:
        return SearchProviderType.TAVILY

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=30.0,
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
        return self._client

    async def search(self, config: SearchConfig) -> List[SearchResult]:
        client = await self._get_client()

        payload = {
            "query": config.query,
            "max_results": config.limit,
            "search_depth": "advanced",
            "include_answer": False,
            "include_images": False,
            "include_raw_content": False,
        }

        if config.recency_days:
            payload["days"] = config.recency_days

        if config.domain_filter:
            payload["include_domains"] = config.domain_filter

        response = await client.post("/search", json=payload)
        response.raise_for_status()
        data = response.json()

        results = []
        for item in data.get("results", []):
            result = SearchResult(
                url=item.get("url", ""),
                title=item.get("title", ""),
                snippet=item.get("content", ""),
                source_type=config.source_type,
                published_date=item.get("published_date"),
                author=item.get("author"),
                credibility=0.8,  # Tavily generally high quality
                relevance=item.get("score", 0.5),
                metadata={
                    "raw_score": item.get("score"),
                    "tavily_id": item.get("id"),
                }
            )
            results.append(result)

        return results

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None