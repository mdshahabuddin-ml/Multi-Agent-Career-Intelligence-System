import json
import logging
from typing import Any, AsyncIterator, Dict, List, Optional, Type, TypeVar

from backend.providers.llm.base import (
    LLMConfig, LLMMessage, LLMProvider, LLMProviderType, LLMResponse, LLMStreamChunk
)

logger = logging.getLogger(__name__)

T = TypeVar('T')


class MockProvider(LLMProvider):
    """Mock LLM provider for testing."""

    def __init__(self, config: LLMConfig, responses: Optional[List[str]] = None):
        super().__init__(config)
        self.responses = responses or [
            "This is a mock response.",
            "Here is another mock response.",
            "Mock structured response: {\"result\": \"success\"}",
        ]
        self.call_count = 0

    @property
    def provider_type(self) -> LLMProviderType:
        return LLMProviderType.MOCK

    async def initialize(self) -> None:
        logger.info("Mock provider initialized")

    async def close(self) -> None:
        pass

    async def generate(
        self,
        messages: List[LLMMessage],
        config: Optional[LLMConfig] = None,
    ) -> LLMResponse:
        self.call_count += 1
        response_text = self.responses[(self.call_count - 1) % len(self.responses)]

        return LLMResponse(
            content=response_text,
            model=self.config.model,
            usage={
                "prompt_tokens": sum(len(m.content) for m in messages) // 4,
                "completion_tokens": len(response_text) // 4,
                "total_tokens": (sum(len(m.content) for m in messages) + len(response_text)) // 4,
            },
            finish_reason="stop",
        )

    async def generate_structured(
        self,
        messages: List[LLMMessage],
        response_model: Type[T],
        config: Optional[LLMConfig] = None,
    ) -> T:
        self.call_count += 1

        schema = response_model.model_json_schema()
        defaults = {}

        for field_name, field_info in schema.get("properties", {}).items():
            field_type = field_info.get("type", "string")
            if field_type == "string":
                defaults[field_name] = f"mock_{field_name}"
            elif field_type == "integer":
                defaults[field_name] = 0
            elif field_type == "number":
                defaults[field_name] = 0.0
            elif field_type == "boolean":
                defaults[field_name] = True
            elif field_type == "array":
                defaults[field_name] = []
            elif field_type == "object":
                defaults[field_name] = {}

        return response_model.model_validate(defaults)

    async def stream(
        self,
        messages: List[LLMMessage],
        config: Optional[LLMConfig] = None,
    ) -> AsyncIterator[LLMStreamChunk]:
        self.call_count += 1
        response_text = self.responses[(self.call_count - 1) % len(self.responses)]

        chunk_size = 10
        for i in range(0, len(response_text), chunk_size):
            chunk = response_text[i:i + chunk_size]
            yield LLMStreamChunk(content=chunk)

        yield LLMStreamChunk(content="", finish_reason="stop")

    async def count_tokens(self, messages: List[LLMMessage]) -> int:
        return sum(len(m.content) for m in messages) // 4

    def add_response(self, response: str) -> None:
        """Add a response to the mock."""
        self.responses.append(response)

    def set_responses(self, responses: List[str]) -> None:
        """Set all responses."""
        self.responses = responses
        self.call_count = 0