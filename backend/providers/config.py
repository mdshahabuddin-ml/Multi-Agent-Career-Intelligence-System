import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from backend.providers.llm import LLMConfig, LLMProviderType
from backend.providers.search import SearchProviderType


@dataclass
class ProviderSettings:
    """Settings for a specific provider."""
    provider: LLMProviderType
    model: str
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    organization: Optional[str] = None
    api_version: Optional[str] = None
    deployment: Optional[str] = None
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    top_p: float = 1.0
    extra_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchProviderSettings:
    """Settings for a search provider."""
    provider: SearchProviderType
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    default_limit: int = 10
    default_recency_days: Optional[int] = None


@dataclass
class LLMSettings:
    """Global LLM settings."""
    default_provider: LLMProviderType
    providers: Dict[LLMProviderType, ProviderSettings] = field(default_factory=dict)
    fallback_providers: List[LLMProviderType] = field(default_factory=list)


@dataclass
class SearchSettings:
    """Global search settings."""
    default_provider: SearchProviderType
    providers: Dict[SearchProviderType, SearchProviderSettings] = field(default_factory=dict)
    fallback_providers: List[SearchProviderType] = field(default_factory=list)


def load_llm_settings() -> LLMSettings:
    """Load LLM settings from environment variables."""
    default_provider_str = os.getenv("LLM_DEFAULT_PROVIDER", "openai")
    try:
        default_provider = LLMProviderType(default_provider_str)
    except ValueError:
        default_provider = LLMProviderType.OPENAI

    settings = LLMSettings(default_provider=default_provider)

    # OpenAI
    if os.getenv("OPENAI_API_KEY"):
        settings.providers[LLMProviderType.OPENAI] = ProviderSettings(
            provider=LLMProviderType.OPENAI,
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            api_key=os.getenv("OPENAI_API_KEY"),
            organization=os.getenv("OPENAI_ORGANIZATION"),
            api_base=os.getenv("OPENAI_API_BASE"),
            temperature=float(os.getenv("OPENAI_TEMPERATURE", "0.7")),
            max_tokens=int(os.getenv("OPENAI_MAX_TOKENS", "0")) or None,
        )

    # Anthropic
    if os.getenv("ANTHROPIC_API_KEY"):
        settings.providers[LLMProviderType.ANTHROPIC] = ProviderSettings(
            provider=LLMProviderType.ANTHROPIC,
            model=os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022"),
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            api_base=os.getenv("ANTHROPIC_API_BASE"),
            temperature=float(os.getenv("ANTHROPIC_TEMPERATURE", "0.7")),
            max_tokens=int(os.getenv("ANTHROPIC_MAX_TOKENS", "0")) or None,
        )

    # Google
    if os.getenv("GOOGLE_API_KEY"):
        settings.providers[LLMProviderType.GOOGLE] = ProviderSettings(
            provider=LLMProviderType.GOOGLE,
            model=os.getenv("GOOGLE_MODEL", "gemini-1.5-pro"),
            api_key=os.getenv("GOOGLE_API_KEY"),
            temperature=float(os.getenv("GOOGLE_TEMPERATURE", "0.7")),
            max_tokens=int(os.getenv("GOOGLE_MAX_TOKENS", "0")) or None,
        )

    # Ollama
    if os.getenv("OLLAMA_BASE_URL"):
        settings.providers[LLMProviderType.OLLAMA] = ProviderSettings(
            provider=LLMProviderType.OLLAMA,
            model=os.getenv("OLLAMA_MODEL", "llama3.1"),
            api_base=os.getenv("OLLAMA_BASE_URL"),
            temperature=float(os.getenv("OLLAMA_TEMPERATURE", "0.7")),
            max_tokens=int(os.getenv("OLLAMA_MAX_TOKENS", "0")) or None,
        )

    # Azure OpenAI
    if os.getenv("AZURE_OPENAI_API_KEY"):
        settings.providers[LLMProviderType.AZURE_OPENAI] = ProviderSettings(
            provider=LLMProviderType.AZURE_OPENAI,
            model=os.getenv("AZURE_OPENAI_MODEL", "gpt-4o"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_base=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
            deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
            temperature=float(os.getenv("AZURE_OPENAI_TEMPERATURE", "0.7")),
            max_tokens=int(os.getenv("AZURE_OPENAI_MAX_TOKENS", "0")) or None,
        )

    # Fallback providers
    fallback_str = os.getenv("LLM_FALLBACK_PROVIDERS", "")
    if fallback_str:
        for p in fallback_str.split(","):
            p = p.strip()
            if p:
                try:
                    settings.fallback_providers.append(LLMProviderType(p))
                except ValueError:
                    pass

    return settings


def load_search_settings() -> SearchSettings:
    """Load search provider settings from environment variables."""
    default_provider_str = os.getenv("SEARCH_DEFAULT_PROVIDER", "tavily")
    try:
        default_provider = SearchProviderType(default_provider_str)
    except ValueError:
        default_provider = SearchProviderType.MOCK

    settings = SearchSettings(default_provider=default_provider)

    # Tavily
    if os.getenv("TAVILY_API_KEY"):
        settings.providers[SearchProviderType.TAVILY] = SearchProviderSettings(
            provider=SearchProviderType.TAVILY,
            api_key=os.getenv("TAVILY_API_KEY"),
            api_base=os.getenv("TAVILY_API_BASE"),
            default_limit=int(os.getenv("TAVILY_DEFAULT_LIMIT", "10")),
            default_recency_days=int(os.getenv("TAVILY_DEFAULT_RECENCY", "0")) or None,
        )

    # Serper
    if os.getenv("SERPER_API_KEY"):
        settings.providers[SearchProviderType.SERPER] = SearchProviderSettings(
            provider=SearchProviderType.SERPER,
            api_key=os.getenv("SERPER_API_KEY"),
            api_base=os.getenv("SERPER_API_BASE"),
            default_limit=int(os.getenv("SERPER_DEFAULT_LIMIT", "10")),
            default_recency_days=int(os.getenv("SERPER_DEFAULT_RECENCY", "0")) or None,
        )

    # Brave
    if os.getenv("BRAVE_API_KEY"):
        settings.providers[SearchProviderType.BRAVE] = SearchProviderSettings(
            provider=SearchProviderType.BRAVE,
            api_key=os.getenv("BRAVE_API_KEY"),
            api_base=os.getenv("BRAVE_API_BASE"),
            default_limit=int(os.getenv("BRAVE_DEFAULT_LIMIT", "10")),
            default_recency_days=int(os.getenv("BRAVE_DEFAULT_RECENCY", "0")) or None,
        )

    # Fallback providers
    fallback_str = os.getenv("SEARCH_FALLBACK_PROVIDERS", "")
    if fallback_str:
        for p in fallback_str.split(","):
            p = p.strip()
            if p:
                try:
                    settings.fallback_providers.append(SearchProviderType(p))
                except ValueError:
                    pass

    return settings


def create_llm_config(settings: ProviderSettings) -> LLMConfig:
    """Create LLMConfig from ProviderSettings."""
    return LLMConfig(
        model=settings.model,
        temperature=settings.temperature,
        max_tokens=settings.max_tokens,
        top_p=settings.top_p,
        extra_params=settings.extra_params,
    )


def create_search_provider(settings: SearchProviderSettings):
    """Create a search provider instance from settings."""
    from backend.providers.search import get_search_registry
    registry = get_search_registry()
    provider_class = registry.get_provider_class(settings.provider)
    if not provider_class:
        raise ValueError(f"Unknown search provider: {settings.provider.value}")

    kwargs = {}
    if settings.api_key:
        kwargs["api_key"] = settings.api_key
    if settings.api_base:
        kwargs["base_url"] = settings.api_base

    return provider_class(**kwargs)


def get_provider_kwargs(settings: ProviderSettings) -> Dict[str, Any]:
    """Get provider-specific kwargs from settings."""
    kwargs = {}
    if settings.api_key:
        kwargs["api_key"] = settings.api_key
    if settings.api_base:
        kwargs["base_url"] = settings.api_base
    if settings.organization:
        kwargs["organization"] = settings.organization
    if settings.api_version:
        kwargs["api_version"] = settings.api_version
    if settings.deployment:
        kwargs["azure_deployment"] = settings.deployment
    return kwargs