import logging
from typing import Any, Dict, List, Optional

import httpx

from backend.providers.search.base import (
    SearchProvider, SearchProviderType, SearchConfig, SearchResult
)

logger = logging.getLogger(__name__)


class BraveSearchProvider(SearchProvider):
    """Brave Search API provider implementation."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.search.brave.com",
        **kwargs
    ):
        super().__init__(api_key=api_key, base_url=base_url, **kwargs)
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def provider_type(self) -> SearchProviderType:
        return SearchProviderType.BRAVE

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=30.0,
                headers={
                    "Accept": "application/json",
                    "X-Subscription-Token": self.api_key
                }
            )
        return self._client

    async def search(self, config: SearchConfig) -> List[SearchResult]:
        client = await self._get_client()

        params = {
            "q": config.query,
            "count": config.limit,
            "country": config.region.upper(),
            "search_lang": config.language,
            "safesearch": "strict" if config.safe_search else "off",
            "text_decorations": False,
        }

        if config.recency_days:
            params["freshness"] = f"pd{config.recency_days}"

        if config.source_type == "news":
            endpoint = "/news/search"
        else:
            endpoint = "/web/search"

        response = await client.get(endpoint, params=params)
        response.raise_for_status()
        data = response.json()

        results = []
        if config.source_type == "news":
            for item in data.get("results", []):
                result = SearchResult(
                    url=item.get("url", ""),
                    title=item.get("title", ""),
                    snippet=item.get("description", ""),
                    source_type="news",
                    published_date=item.get("age"),
                    credibility=0.8,
                    relevance=0.75,
                    metadata={
                        "source": item.get("source"),
                        "brave_type": "news",
                    }
                )
                results.append(result)
        else:
            for item in data.get("web", {}).get("results", []):
                result = SearchResult(
                    url=item.get("url", ""),
                    title=item.get("title", ""),
                    snippet=item.get("description", ""),
                    source_type=config.source_type,
                    published_date=item.get("age"),
                    credibility=0.75,
                    relevance=0.8,
                    metadata={
                        "brave_type": "web",
                        "family_friendly": item.get("family_friendly", True),
                    }
                )
                results.append(result)

        return results[:config.limit]

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None