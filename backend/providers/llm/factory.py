import logging
from typing import Any, Dict, List, Optional, Type

from backend.providers.llm.base import LLMConfig, LLMProvider, LLMProviderType

logger = logging.getLogger(__name__)


class ProviderRegistry:
    """Registry for LLM providers."""

    def __init__(self):
        self._providers: Dict[LLMProviderType, Type[LLMProvider]] = {}
        self._instances: Dict[str, LLMProvider] = {}
        self._default_provider: Optional[LLMProviderType] = None

    def register(self, provider_type: LLMProviderType, provider_class: Type[LLMProvider]) -> None:
        """Register a provider class."""
        self._providers[provider_type] = provider_class
        logger.info(f"Registered provider: {provider_type.value}")

    def unregister(self, provider_type: LLMProviderType) -> None:
        """Unregister a provider."""
        if provider_type in self._providers:
            del self._providers[provider_type]
            logger.info(f"Unregistered provider: {provider_type.value}")

    def get_provider_class(self, provider_type: LLMProviderType) -> Optional[Type[LLMProvider]]:
        """Get provider class by type."""
        return self._providers.get(provider_type)

    def list_providers(self) -> List[LLMProviderType]:
        """List all registered provider types."""
        return list(self._providers.keys())

    def set_default(self, provider_type: LLMProviderType) -> None:
        """Set default provider."""
        if provider_type in self._providers:
            self._default_provider = provider_type
            logger.info(f"Set default provider: {provider_type.value}")
        else:
            raise ValueError(f"Provider not registered: {provider_type.value}")

    def get_default(self) -> Optional[LLMProviderType]:
        """Get default provider type."""
        return self._default_provider


class LLMProviderFactory:
    """Factory for creating LLM provider instances."""

    def __init__(self, registry: ProviderRegistry):
        self.registry = registry

    def create(
        self,
        provider_type: LLMProviderType,
        config: LLMConfig,
        **kwargs: Any,
    ) -> LLMProvider:
        """Create a provider instance."""
        provider_class = self.registry.get_provider_class(provider_type)
        if not provider_class:
            raise ValueError(f"Unknown provider type: {provider_type.value}")

        instance = provider_class(config, **kwargs)
        logger.info(f"Created provider instance: {provider_type.value}")
        return instance

    async def create_and_initialize(
        self,
        provider_type: LLMProviderType,
        config: LLMConfig,
        **kwargs: Any,
    ) -> LLMProvider:
        """Create and initialize a provider instance."""
        provider = self.create(provider_type, config, **kwargs)
        await provider.initialize()
        return provider

    def create_from_config(
        self,
        config_dict: Dict[str, Any],
    ) -> LLMProvider:
        """Create provider from configuration dictionary."""
        provider_type = LLMProviderType(config_dict.get("provider", "openai"))
        model = config_dict.get("model", "gpt-4o-mini")

        llm_config = LLMConfig(
            model=model,
            temperature=config_dict.get("temperature", 0.7),
            max_tokens=config_dict.get("max_tokens"),
            top_p=config_dict.get("top_p", 1.0),
            frequency_penalty=config_dict.get("frequency_penalty", 0.0),
            presence_penalty=config_dict.get("presence_penalty", 0.0),
            stop=config_dict.get("stop"),
            response_format=config_dict.get("response_format"),
            tools=config_dict.get("tools"),
            tool_choice=config_dict.get("tool_choice"),
            seed=config_dict.get("seed"),
            extra_params=config_dict.get("extra_params"),
        )

        kwargs = {k: v for k, v in config_dict.items() if k not in [
            "provider", "model", "temperature", "max_tokens", "top_p",
            "frequency_penalty", "presence_penalty", "stop", "response_format",
            "tools", "tool_choice", "seed", "extra_params",
        ]}

        return self.create(provider_type, llm_config, **kwargs)


# Global registry instance
_provider_registry: Optional[ProviderRegistry] = None


def get_provider_registry() -> ProviderRegistry:
    """Get the global provider registry."""
    global _provider_registry
    if _provider_registry is None:
        _provider_registry = ProviderRegistry()
        _register_default_providers(_provider_registry)
    return _provider_registry


def _register_default_providers(registry: ProviderRegistry) -> None:
    """Register default providers."""
    try:
        from backend.providers.llm.openai import OpenAIProvider
        registry.register(LLMProviderType.OPENAI, OpenAIProvider)
    except ImportError:
        pass

    try:
        from backend.providers.llm.anthropic import AnthropicProvider
        registry.register(LLMProviderType.ANTHROPIC, AnthropicProvider)
    except ImportError:
        pass

    try:
        from backend.providers.llm.google import GoogleProvider
        registry.register(LLMProviderType.GOOGLE, GoogleProvider)
    except ImportError:
        pass

    try:
        from backend.providers.llm.ollama import OllamaProvider
        registry.register(LLMProviderType.OLLAMA, OllamaProvider)
    except ImportError:
        pass

    try:
        from backend.providers.llm.azure_openai import AzureOpenAIProvider
        registry.register(LLMProviderType.AZURE_OPENAI, AzureOpenAIProvider)
    except ImportError:
        pass

    try:
        from backend.providers.llm.mock import MockProvider
        registry.register(LLMProviderType.MOCK, MockProvider)
    except ImportError:
        pass


def get_llm_factory() -> LLMProviderFactory:
    """Get the LLM provider factory."""
    return LLMProviderFactory(get_provider_registry())