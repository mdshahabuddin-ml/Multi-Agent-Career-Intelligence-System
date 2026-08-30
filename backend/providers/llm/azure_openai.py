import json
import logging
from typing import Any, AsyncIterator, Dict, List, Optional, Type, TypeVar

from backend.providers.llm.base import (
    LLMConfig, LLMMessage, LLMProvider, LLMProviderType, LLMResponse, LLMStreamChunk
)
from backend.providers.llm.openai import OpenAIProvider

logger = logging.getLogger(__name__)

T = TypeVar('T')


class AzureOpenAIProvider(OpenAIProvider):
    """Azure OpenAI LLM provider implementation."""

    def __init__(
        self,
        config: LLMConfig,
        api_key: str,
        azure_endpoint: str,
        api_version: str = "2024-02-15-preview",
        azure_deployment: Optional[str] = None,
    ):
        super().__init__(config, api_key)
        self.azure_endpoint = azure_endpoint.rstrip("/")
        self.api_version = api_version
        self.azure_deployment = azure_deployment or config.model

    @property
    def provider_type(self) -> LLMProviderType:
        return LLMProviderType.AZURE_OPENAI

    async def initialize(self) -> None:
        try:
            import openai
            self._client = openai.AsyncAzureOpenAI(
                api_key=self.api_key,
                azure_endpoint=self.azure_endpoint,
                api_version=self.api_version,
            )
            logger.info("Azure OpenAI provider initialized")
        except ImportError:
            raise ImportError("openai package not installed. Run: pip install openai")

    async def generate(
        self,
        messages: List[LLMMessage],
        config: Optional[LLMConfig] = None,
    ) -> LLMResponse:
        merged_config = self._merge_config(config)
        openai_messages = self._convert_messages(messages)

        kwargs = {
            "model": self.azure_deployment,
            "messages": openai_messages,
            "temperature": merged_config.temperature,
            "top_p": merged_config.top_p,
        }

        if merged_config.max_tokens:
            kwargs["max_tokens"] = merged_config.max_tokens
        if merged_config.frequency_penalty:
            kwargs["frequency_penalty"] = merged_config.frequency_penalty
        if merged_config.presence_penalty:
            kwargs["presence_penalty"] = merged_config.presence_penalty
        if merged_config.stop:
            kwargs["stop"] = merged_config.stop
        if merged_config.response_format:
            kwargs["response_format"] = merged_config.response_format
        if merged_config.tools:
            kwargs["tools"] = self._convert_tools(merged_config.tools)
        if merged_config.tool_choice:
            kwargs["tool_choice"] = merged_config.tool_choice
        if merged_config.seed:
            kwargs["seed"] = merged_config.seed
        if merged_config.extra_params:
            kwargs.update(merged_config.extra_params)

        response = await self._client.chat.completions.create(**kwargs)

        choice = response.choices[0]
        tool_calls = None
        if choice.message.tool_calls:
            tool_calls = [
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in choice.message.tool_calls
            ]

        return LLMResponse(
            content=choice.message.content or "",
            model=response.model,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            },
            finish_reason=choice.finish_reason,
            tool_calls=tool_calls,
        )

    async def stream(
        self,
        messages: List[LLMMessage],
        config: Optional[LLMConfig] = None,
    ) -> AsyncIterator[LLMStreamChunk]:
        merged_config = self._merge_config(config)
        openai_messages = self._convert_messages(messages)

        kwargs = {
            "model": self.azure_deployment,
            "messages": openai_messages,
            "temperature": merged_config.temperature,
            "top_p": merged_config.top_p,
            "stream": True,
        }

        if merged_config.max_tokens:
            kwargs["max_tokens"] = merged_config.max_tokens
        if merged_config.frequency_penalty:
            kwargs["frequency_penalty"] = merged_config.frequency_penalty
        if merged_config.presence_penalty:
            kwargs["presence_penalty"] = merged_config.presence_penalty
        if merged_config.stop:
            kwargs["stop"] = merged_config.stop
        if merged_config.tools:
            kwargs["tools"] = self._convert_tools(merged_config.tools)
        if merged_config.tool_choice:
            kwargs["tool_choice"] = merged_config.tool_choice
        if merged_config.seed:
            kwargs["seed"] = merged_config.seed
        if merged_config.extra_params:
            kwargs.update(merged_config.extra_params)

        stream = await self._client.chat.completions.create(**kwargs)

        async for chunk in stream:
            if chunk.choices:
                choice = chunk.choices[0]
                if choice.delta.content:
                    yield LLMStreamChunk(
                        content=choice.delta.content,
                        finish_reason=choice.finish_reason,
                    )
                if choice.delta.tool_calls:
                    tool_calls = [
                        {
                            "id": tc.id,
                            "type": tc.type,
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in choice.delta.tool_calls
                    ]
                    yield LLMStreamChunk(
                        content="",
                        finish_reason=choice.finish_reason,
                        tool_calls=tool_calls,
                    )