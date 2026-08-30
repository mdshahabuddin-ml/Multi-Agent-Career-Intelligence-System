import logging
from typing import Any, AsyncIterator, Dict, List, Optional, Type, TypeVar

from backend.providers.llm import (
    LLMProvider,
    LLMProviderType,
    LLMConfig,
    LLMMessage,
    LLMResponse,
    LLMStreamChunk,
    get_llm_factory,
)
from backend.providers.config import LLMSettings, load_llm_settings, create_llm_config, get_provider_kwargs

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ProviderManager:
    """Manages LLM provider lifecycle and provides unified interface."""

    def __init__(self, settings: Optional[LLMSettings] = None):
        self.settings = settings or load_llm_settings()
        self.factory = get_llm_factory()
        self._providers: Dict[LLMProviderType, LLMProvider] = {}
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize all configured providers."""
        if self._initialized:
            return

        for provider_type, provider_settings in self.settings.providers.items():
            try:
                config = create_llm_config(provider_settings)
                kwargs = get_provider_kwargs(provider_settings)
                provider = await self.factory.create_and_initialize(provider_type, config, **kwargs)
                self._providers[provider_type] = provider
                logger.info(f"Initialized provider: {provider_type.value}")
            except Exception as e:
                logger.warning(f"Failed to initialize provider {provider_type.value}: {e}")

        if not self._providers:
            # Fallback to mock provider for testing
            from backend.providers.llm.mock import MockProvider
            mock_config = LLMConfig(model="mock")
            mock_provider = MockProvider(mock_config)
            await mock_provider.initialize()
            self._providers[LLMProviderType.MOCK] = mock_provider
            logger.warning("No providers configured, using mock provider")

        self._initialized = True

    async def close(self) -> None:
        """Close all providers."""
        for provider_type, provider in self._providers.items():
            try:
                await provider.close()
                logger.info(f"Closed provider: {provider_type.value}")
            except Exception as e:
                logger.warning(f"Error closing provider {provider_type.value}: {e}")
        self._providers.clear()
        self._initialized = False

    def get_provider(self, provider_type: Optional[LLMProviderType] = None) -> LLMProvider:
        """Get a provider instance."""
        if not self._initialized:
            raise RuntimeError("ProviderManager not initialized. Call initialize() first.")

        target_type = provider_type or self.settings.default_provider

        if target_type not in self._providers:
            # Try fallback providers
            for fallback in self.settings.fallback_providers:
                if fallback in self._providers:
                    logger.warning(f"Provider {target_type.value} not available, using fallback: {fallback.value}")
                    return self._providers[fallback]
            # Try default provider
            if self.settings.default_provider in self._providers:
                logger.warning(f"Provider {target_type.value} not available, using default: {self.settings.default_provider.value}")
                return self._providers[self.settings.default_provider]
            # Use any available provider
            if self._providers:
                available = next(iter(self._providers.values()))
                logger.warning(f"Provider {target_type.value} not available, using: {available.provider_type.value}")
                return available

        return self._providers[target_type]

    def list_available_providers(self) -> List[LLMProviderType]:
        """List available provider types."""
        return list(self._providers.keys())

    async def generate(
        self,
        messages: List[LLMMessage],
        config: Optional[LLMConfig] = None,
        provider_type: Optional[LLMProviderType] = None,
    ) -> LLMResponse:
        """Generate a completion."""
        provider = self.get_provider(provider_type)
        return await provider.generate(messages, config)

    async def generate_structured(
        self,
        messages: List[LLMMessage],
        response_model: Type[T],
        config: Optional[LLMConfig] = None,
        provider_type: Optional[LLMProviderType] = None,
    ) -> T:
        """Generate a structured completion."""
        provider = self.get_provider(provider_type)
        return await provider.generate_structured(messages, response_model, config)

    async def stream(
        self,
        messages: List[LLMMessage],
        config: Optional[LLMConfig] = None,
        provider_type: Optional[LLMProviderType] = None,
    ) -> AsyncIterator[LLMStreamChunk]:
        """Stream a completion."""
        provider = self.get_provider(provider_type)
        async for chunk in provider.stream(messages, config):
            yield chunk

    async def generate_with_fallback(
        self,
        messages: List[LLMMessage],
        config: Optional[LLMConfig] = None,
        preferred_provider: Optional[LLMProviderType] = None,
    ) -> LLMResponse:
        """Generate with automatic fallback on failure."""
        providers_to_try = []

        if preferred_provider and preferred_provider in self._providers:
            providers_to_try.append(preferred_provider)

        if self.settings.default_provider in self._providers:
            if self.settings.default_provider not in providers_to_try:
                providers_to_try.append(self.settings.default_provider)

        for fallback in self.settings.fallback_providers:
            if fallback in self._providers and fallback not in providers_to_try:
                providers_to_try.append(fallback)

        for provider in self._providers.values():
            if provider.provider_type not in providers_to_try:
                providers_to_try.append(provider.provider_type)

        last_error = None
        for provider_type in providers_to_try:
            try:
                provider = self._providers[provider_type]
                logger.info(f"Trying provider: {provider_type.value}")
                return await provider.generate(messages, config)
            except Exception as e:
                last_error = e
                logger.warning(f"Provider {provider_type.value} failed: {e}")
                continue

        raise RuntimeError(f"All providers failed. Last error: {last_error}")

    async def generate_structured_with_fallback(
        self,
        messages: List[LLMMessage],
        response_model: Type[T],
        config: Optional[LLMConfig] = None,
        preferred_provider: Optional[LLMProviderType] = None,
    ) -> T:
        """Generate structured with automatic fallback on failure."""
        providers_to_try = []

        if preferred_provider and preferred_provider in self._providers:
            providers_to_try.append(preferred_provider)

        if self.settings.default_provider in self._providers:
            if self.settings.default_provider not in providers_to_try:
                providers_to_try.append(self.settings.default_provider)

        for fallback in self.settings.fallback_providers:
            if fallback in self._providers and fallback not in providers_to_try:
                providers_to_try.append(fallback)

        for provider in self._providers.values():
            if provider.provider_type not in providers_to_try:
                providers_to_try.append(provider.provider_type)

        last_error = None
        for provider_type in providers_to_try:
            try:
                provider = self._providers[provider_type]
                logger.info(f"Trying provider for structured: {provider_type.value}")
                return await provider.generate_structured(messages, response_model, config)
            except Exception as e:
                last_error = e
                logger.warning(f"Provider {provider_type.value} failed for structured: {e}")
                continue

        raise RuntimeError(f"All providers failed for structured generation. Last error: {last_error}")


# Global provider manager instance
_provider_manager: Optional[ProviderManager] = None


def get_provider_manager() -> ProviderManager:
    """Get the global provider manager."""
    global _provider_manager
    if _provider_manager is None:
        _provider_manager = ProviderManager()
    return _provider_manager


async def initialize_providers(settings: Optional[LLMSettings] = None) -> ProviderManager:
    """Initialize the global provider manager."""
    global _provider_manager
    _provider_manager = ProviderManager(settings)
    await _provider_manager.initialize()
    return _provider_manager


async def close_providers() -> None:
    """Close the global provider manager."""
    global _provider_manager
    if _provider_manager:
        await _provider_manager.close()
        _provider_manager = None