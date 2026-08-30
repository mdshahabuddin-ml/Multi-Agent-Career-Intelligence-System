from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, List, Optional, Type, TypeVar
from dataclasses import dataclass
from enum import Enum

T = TypeVar('T')


class LLMProviderType(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    OLLAMA = "ollama"
    AZURE_OPENAI = "azure_openai"
    MOCK = "mock"


@dataclass
class LLMMessage:
    role: str
    content: str
    name: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None


@dataclass
class LLMResponse:
    content: str
    model: str
    usage: Dict[str, int]
    finish_reason: str
    tool_calls: Optional[List[Dict[str, Any]]] = None


@dataclass
class LLMStreamChunk:
    content: str
    finish_reason: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None


@dataclass
class LLMConfig:
    model: str
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    stop: Optional[List[str]] = None
    response_format: Optional[Dict[str, Any]] = None
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[str] = None
    seed: Optional[int] = None
    extra_params: Dict[str, Any] = None


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    def __init__(self, config: LLMConfig):
        self.config = config
        self._client = None

    @property
    @abstractmethod
    def provider_type(self) -> LLMProviderType:
        pass

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the provider client."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close the provider client."""
        pass

    @abstractmethod
    async def generate(
        self,
        messages: List[LLMMessage],
        config: Optional[LLMConfig] = None,
    ) -> LLMResponse:
        """Generate a completion."""
        pass

    @abstractmethod
    async def generate_structured(
        self,
        messages: List[LLMMessage],
        response_model: Type[T],
        config: Optional[LLMConfig] = None,
    ) -> T:
        """Generate a structured completion using Pydantic model."""
        pass

    @abstractmethod
    async def stream(
        self,
        messages: List[LLMMessage],
        config: Optional[LLMConfig] = None,
    ) -> AsyncIterator[LLMStreamChunk]:
        """Stream a completion."""
        pass

    @abstractmethod
    async def count_tokens(self, messages: List[LLMMessage]) -> int:
        """Count tokens in messages."""
        pass

    def _merge_config(self, config: Optional[LLMConfig]) -> LLMConfig:
        """Merge provided config with default config."""
        if config is None:
            return self.config
        merged = LLMConfig(
            model=config.model or self.config.model,
            temperature=config.temperature if config.temperature is not None else self.config.temperature,
            max_tokens=config.max_tokens or self.config.max_tokens,
            top_p=config.top_p if config.top_p is not None else self.config.top_p,
            frequency_penalty=config.frequency_penalty if config.frequency_penalty is not None else self.config.frequency_penalty,
            presence_penalty=config.presence_penalty if config.presence_penalty is not None else self.config.presence_penalty,
            stop=config.stop or self.config.stop,
            response_format=config.response_format or self.config.response_format,
            tools=config.tools or self.config.tools,
            tool_choice=config.tool_choice or self.config.tool_choice,
            seed=config.seed or self.config.seed,
            extra_params={**(self.config.extra_params or {}), **(config.extra_params or {})},
        )
        return merged