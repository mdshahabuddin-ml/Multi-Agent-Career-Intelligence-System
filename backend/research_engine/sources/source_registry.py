from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum as PyEnum
import logging

from backend.research_engine.state.research_context import ResearchSourceType, SourceMetadata

logger = logging.getLogger(__name__)


class SourceProviderType(str, PyEnum):
    """Types of source providers."""
    SEARCH_API = "search_api"  # Tavily, Serper, Google
    NEWS_API = "news_api"  # NewsAPI, GNews
    ACADEMIC_API = "academic_api"  # arXiv, Semantic Scholar
    COMPANY_API = "company_api"  # LinkedIn, Glassdoor
    JOB_API = "job_api"  # Indeed, LinkedIn Jobs
    CUSTOM = "custom"


@dataclass
class SourceProviderConfig:
    """Configuration for a source provider."""
    name: str
    provider_type: SourceProviderType
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    rate_limit: int = 60  # requests per minute
    timeout_seconds: int = 30
    enabled: bool = True
    custom_headers: Dict[str, str] = field(default_factory=dict)
    parameters: Dict[str, Any] = field(default_factory=dict)


class SourceProvider:
    """Base class for source providers."""

    def __init__(self, config: SourceProviderConfig):
        self.config = config
        self.name = config.name

    async def search(
        self,
        query: str,
        limit: int = 10,
        **kwargs
    ) -> List[SourceMetadata]:
        """Search for sources."""
        raise NotImplementedError

    async def fetch(self, url: str) -> Optional[str]:
        """Fetch content from URL."""
        raise NotImplementedError


class SourceRegistry:
    """Registry of source providers and source management."""

    def __init__(self):
        self._providers: Dict[str, SourceProvider] = {}
        self._provider_configs: Dict[str, SourceProviderConfig] = {}
        self._source_handlers: Dict[ResearchSourceType, List[str]] = {}

    def register_provider(self, provider: SourceProvider):
        """Register a source provider."""
        self._providers[provider.name] = provider
        logger.info(f"Registered source provider: {provider.name}")

    def unregister_provider(self, name: str) -> bool:
        """Unregister a source provider."""
        if name in self._providers:
            del self._providers[name]
            logger.info(f"Unregistered source provider: {name}")
            return True
        return False

    def get_provider(self, name: str) -> Optional[SourceProvider]:
        """Get a provider by name."""
        return self._providers.get(name)

    def list_providers(self) -> List[Dict[str, Any]]:
        """List all registered providers."""
        return [
            {
                "name": p.name,
                "type": p.config.provider_type.value,
                "enabled": p.config.enabled,
                "rate_limit": p.config.rate_limit,
            }
            for p in self._providers.values()
        ]

    def register_source_type_handler(self, source_type: ResearchSourceType, provider_names: List[str]):
        """Register providers for a source type."""
        self._source_handlers[source_type] = provider_names

    def get_providers_for_type(self, source_type: ResearchSourceType) -> List[SourceProvider]:
        """Get providers for a source type."""
        provider_names = self._source_handlers.get(source_type, [])
        return [self._providers[name] for name in provider_names if name in self._providers]

    async def search_all(
        self,
        query: str,
        source_types: Optional[List[ResearchSourceType]] = None,
        limit: int = 10,
        **kwargs
    ) -> List[SourceMetadata]:
        """Search across all relevant providers."""
        if source_types is None:
            source_types = list(ResearchSourceType)

        all_sources = []

        for source_type in source_types:
            providers = self.get_providers_for_type(source_type)
            for provider in providers:
                if not provider.config.enabled:
                    continue

                try:
                    sources = await provider.search(query, limit=limit, **kwargs)
                    all_sources.extend(sources)
                except Exception as e:
                    logger.error(f"Provider {provider.name} failed: {e}")

        # Deduplicate by URL
        seen_urls = set()
        unique_sources = []
        for source in all_sources:
            if source.url not in seen_urls:
                seen_urls.add(source.url)
                unique_sources.append(source)

        return unique_sources[:limit]

    def configure_provider(self, config: SourceProviderConfig):
        """Configure a provider (stores config for later instantiation)."""
        self._provider_configs[config.name] = config

    def get_provider_config(self, name: str) -> Optional[SourceProviderConfig]:
        """Get provider configuration."""
        return self._provider_configs.get(name)


# Default provider registry instance
default_registry = SourceRegistry()


# Built-in source configurations
DEFAULT_SOURCE_CONFIGS = {
    "tavily": SourceProviderConfig(
        name="tavily",
        provider_type=SourceProviderType.SEARCH_API,
        base_url="https://api.tavily.com",
        rate_limit=60,
        timeout_seconds=30,
        parameters={"search_depth": "advanced"},
    ),
    "serper": SourceProviderConfig(
        name="serper",
        provider_type=SourceProviderType.SEARCH_API,
        base_url="https://google.serper.dev",
        rate_limit=100,
        timeout_seconds=20,
    ),
    "newsapi": SourceProviderConfig(
        name="newsapi",
        provider_type=SourceProviderType.NEWS_API,
        base_url="https://newsapi.org/v2",
        rate_limit=60,
        timeout_seconds=20,
    ),
    "arxiv": SourceProviderConfig(
        name="arxiv",
        provider_type=SourceProviderType.ACADEMIC_API,
        base_url="http://export.arxiv.org/api",
        rate_limit=30,
        timeout_seconds=30,
    ),
    "semantic_scholar": SourceProviderConfig(
        name="semantic_scholar",
        provider_type=SourceProviderType.ACADEMIC_API,
        base_url="https://api.semanticscholar.org/graph/v1",
        rate_limit=100,
        timeout_seconds=30,
    ),
    "linkedin_jobs": SourceProviderConfig(
        name="linkedin_jobs",
        provider_type=SourceProviderType.JOB_API,
        base_url="https://api.linkedin.com/v2",
        rate_limit=30,
        timeout_seconds=30,
    ),
}