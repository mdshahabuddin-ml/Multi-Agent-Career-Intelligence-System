import logging
from typing import Any, Dict, List, Optional

import httpx

from backend.providers.search.base import (
    SearchProvider, SearchProviderType, SearchConfig, SearchResult
)

logger = logging.getLogger(__name__)


class SerperSearchProvider(SearchProvider):
    """Serper.dev search provider implementation."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://google.serper.dev",
        **kwargs
    ):
        super().__init__(api_key=api_key, base_url=base_url, **kwargs)
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def provider_type(self) -> SearchProviderType:
        return SearchProviderType.SERPER

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=30.0,
                headers={"X-API-KEY": self.api_key}
            )
        return self._client

    async def search(self, config: SearchConfig) -> List[SearchResult]:
        client = await self._get_client()

        payload = {
            "q": config.query,
            "num": config.limit,
            "gl": config.region,
            "hl": config.language,
            "safe": "active" if config.safe_search else "off",
        }

        if config.recency_days:
            payload["tbs"] = f"qdr:d{config.recency_days}"

        endpoint = "/search"
        if config.source_type == "news":
            endpoint = "/news"
        elif config.source_type == "academic":
            endpoint = "/scholar"

        response = await client.post(endpoint, json=payload)
        response.raise_for_status()
        data = response.json()

        results = []
        for item in data.get("organic", []):
            result = SearchResult(
                url=item.get("link", ""),
                title=item.get("title", ""),
                snippet=item.get("snippet", ""),
                source_type=config.source_type,
                published_date=item.get("date"),
                credibility=0.75,
                relevance=0.8,
                metadata={
                    "position": item.get("position"),
                    "serper_type": "organic",
                }
            )
            results.append(result)

        # Also include news results if searching news
        if config.source_type == "news":
            for item in data.get("news", []):
                result = SearchResult(
                    url=item.get("link", ""),
                    title=item.get("title", ""),
                    snippet=item.get("snippet", ""),
                    source_type="news",
                    published_date=item.get("date"),
                    credibility=0.8,
                    relevance=0.75,
                    metadata={
                        "source": item.get("source"),
                        "serper_type": "news",
                    }
                )
                results.append(result)

        return results[:config.limit]

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None