import json
import logging
from typing import Any, AsyncIterator, Dict, List, Optional, Type, TypeVar

from backend.providers.llm.base import (
    LLMConfig, LLMMessage, LLMProvider, LLMProviderType, LLMResponse, LLMStreamChunk
)

logger = logging.getLogger(__name__)

T = TypeVar('T')


class OpenAIProvider(LLMProvider):
    """OpenAI LLM provider implementation."""

    def __init__(self, config: LLMConfig, api_key: str, organization: Optional[str] = None, base_url: Optional[str] = None):
        super().__init__(config)
        self.api_key = api_key
        self.organization = organization
        self.base_url = base_url

    @property
    def provider_type(self) -> LLMProviderType:
        return LLMProviderType.OPENAI

    async def initialize(self) -> None:
        try:
            import openai
            self._client = openai.AsyncOpenAI(
                api_key=self.api_key,
                organization=self.organization,
                base_url=self.base_url,
            )
            logger.info("OpenAI provider initialized")
        except ImportError:
            raise ImportError("openai package not installed. Run: pip install openai")

    async def close(self) -> None:
        if self._client:
            await self._client.close()
            self._client = None

    def _convert_messages(self, messages: List[LLMMessage]) -> List[Dict[str, Any]]:
        """Convert LLMMessage to OpenAI format."""
        converted = []
        for msg in messages:
            converted_msg = {
                "role": msg.role,
                "content": msg.content,
            }
            if msg.name:
                converted_msg["name"] = msg.name
            if msg.tool_calls:
                converted_msg["tool_calls"] = msg.tool_calls
            if msg.tool_call_id:
                converted_msg["tool_call_id"] = msg.tool_call_id
            converted.append(converted_msg)
        return converted

    def _convert_tools(self, tools: Optional[List[Dict[str, Any]]]) -> Optional[List[Dict[str, Any]]]:
        """Convert tools to OpenAI format."""
        if not tools:
            return None
        return tools

    async def generate(
        self,
        messages: List[LLMMessage],
        config: Optional[LLMConfig] = None,
    ) -> LLMResponse:
        merged_config = self._merge_config(config)
        openai_messages = self._convert_messages(messages)

        kwargs = {
            "model": merged_config.model,
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

    async def generate_structured(
        self,
        messages: List[LLMMessage],
        response_model: Type[T],
        config: Optional[LLMConfig] = None,
    ) -> T:
        merged_config = self._merge_config(config)

        schema = response_model.model_json_schema()
        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": response_model.__name__,
                "schema": schema,
                "strict": True,
            },
        }

        merged_config.response_format = response_format

        response = await self.generate(messages, merged_config)

        try:
            parsed = json.loads(response.content)
            return response_model.model_validate(parsed)
        except Exception as e:
            logger.error(f"Failed to parse structured response: {e}")
            raise

    async def stream(
        self,
        messages: List[LLMMessage],
        config: Optional[LLMConfig] = None,
    ) -> AsyncIterator[LLMStreamChunk]:
        merged_config = self._merge_config(config)
        openai_messages = self._convert_messages(messages)

        kwargs = {
            "model": merged_config.model,
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

    async def count_tokens(self, messages: List[LLMMessage]) -> int:
        try:
            import tiktoken
            encoding = tiktoken.encoding_for_model(self.config.model)
        except Exception:
            encoding = tiktoken.get_encoding("cl100k_base")

        total = 0
        for msg in messages:
            total += len(encoding.encode(msg.content))
            if msg.role:
                total += 4
        return total