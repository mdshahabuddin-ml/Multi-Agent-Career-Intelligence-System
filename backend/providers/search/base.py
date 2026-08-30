from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum


class SearchProviderType(str, Enum):
    TAVILY = "tavily"
    SERPER = "serper"
    BRAVE = "brave"
    GOOGLE_CSE = "google_cse"
    BING = "bing"
    DUCKDUCKGO = "duckduckgo"
    MOCK = "mock"


@dataclass
class SearchResult:
    url: str
    title: str
    snippet: str
    source_type: str = "web"
    published_date: Optional[str] = None
    author: Optional[str] = None
    domain: Optional[str] = None
    credibility: float = 0.5
    relevance: float = 0.5
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.domain is None and self.url:
            from urllib.parse import urlparse
            try:
                self.domain = urlparse(self.url).netloc.lower().replace("www.", "")
            except Exception:
                self.domain = "unknown"


@dataclass
class SearchConfig:
    query: str
    limit: int = 10
    source_type: str = "web"
    recency_days: Optional[int] = None
    domain_filter: Optional[List[str]] = None
    language: str = "en"
    region: str = "us"
    safe_search: bool = True
    extra_params: Dict[str, Any] = None


class SearchProvider(ABC):
    """Abstract base class for search providers."""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, **kwargs):
        self.api_key = api_key
        self.base_url = base_url
        self.config = kwargs

    @property
    @abstractmethod
    def provider_type(self) -> SearchProviderType:
        pass

    @abstractmethod
    async def search(self, config: SearchConfig) -> List[SearchResult]:
        """Perform a search."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close the provider."""
        pass


class SearchProviderRegistry:
    """Registry for search providers."""

    def __init__(self):
        self._providers: Dict[SearchProviderType, type] = {}
        self._instances: Dict[str, SearchProvider] = {}

    def register(self, provider_type: SearchProviderType, provider_class: type) -> None:
        self._providers[provider_type] = provider_class

    def get_provider_class(self, provider_type: SearchProviderType) -> Optional[type]:
        return self._providers.get(provider_type)

    def list_providers(self) -> List[SearchProviderType]:
        return list(self._providers.keys())


_search_registry: Optional[SearchProviderRegistry] = None


def get_search_registry() -> SearchProviderRegistry:
    global _search_registry
    if _search_registry is None:
        _search_registry = SearchProviderRegistry()
        _register_default_search_providers(_search_registry)
    return _search_registry


def _register_default_search_providers(registry: SearchProviderRegistry) -> None:
    try:
        from backend.providers.search.tavily import TavilySearchProvider
        registry.register(SearchProviderType.TAVILY, TavilySearchProvider)
    except ImportError:
        pass

    try:
        from backend.providers.search.serper import SerperSearchProvider
        registry.register(SearchProviderType.SERPER, SerperSearchProvider)
    except ImportError:
        pass

    try:
        from backend.providers.search.brave import BraveSearchProvider
        registry.register(SearchProviderType.BRAVE, BraveSearchProvider)
    except ImportError:
        pass

    try:
        from backend.providers.search.mock import MockSearchProvider
        registry.register(SearchProviderType.MOCK, MockSearchProvider)
    except ImportError:
        pass