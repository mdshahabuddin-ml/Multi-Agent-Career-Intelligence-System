import json
import logging
from typing import Any, AsyncIterator, Dict, List, Optional, Type, TypeVar

from backend.providers.llm.base import (
    LLMConfig, LLMMessage, LLMProvider, LLMProviderType, LLMResponse, LLMStreamChunk
)

logger = logging.getLogger(__name__)

T = TypeVar('T')


class AnthropicProvider(LLMProvider):
    """Anthropic LLM provider implementation."""

    def __init__(self, config: LLMConfig, api_key: str, base_url: Optional[str] = None):
        super().__init__(config)
        self.api_key = api_key
        self.base_url = base_url

    @property
    def provider_type(self) -> LLMProviderType:
        return LLMProviderType.ANTHROPIC

    async def initialize(self) -> None:
        try:
            import anthropic
            self._client = anthropic.AsyncAnthropic(
                api_key=self.api_key,
                base_url=self.base_url,
            )
            logger.info("Anthropic provider initialized")
        except ImportError:
            raise ImportError("anthropic package not installed. Run: pip install anthropic")

    async def close(self) -> None:
        if self._client:
            await self._client.close()
            self._client = None

    def _convert_messages(self, messages: List[LLMMessage]) -> List[Dict[str, Any]]:
        """Convert LLMMessage to Anthropic format."""
        converted = []
        system_content = None

        for msg in messages:
            if msg.role == "system":
                system_content = msg.content
            else:
                converted.append({
                    "role": msg.role,
                    "content": msg.content,
                })

        if system_content:
            converted.insert(0, {"role": "system", "content": system_content})

        return converted

    def _convert_tools(self, tools: Optional[List[Dict[str, Any]]]) -> Optional[List[Dict[str, Any]]]:
        """Convert tools to Anthropic format."""
        if not tools:
            return None
        anthropic_tools = []
        for tool in tools:
            if tool.get("type") == "function":
                func = tool["function"]
                anthropic_tools.append({
                    "name": func["name"],
                    "description": func.get("description", ""),
                    "input_schema": func.get("parameters", {"type": "object", "properties": {}}),
                })
        return anthropic_tools if anthropic_tools else None

    async def generate(
        self,
        messages: List[LLMMessage],
        config: Optional[LLMConfig] = None,
    ) -> LLMResponse:
        merged_config = self._merge_config(config)
        anthropic_messages = self._convert_messages(messages)

        kwargs = {
            "model": merged_config.model,
            "messages": anthropic_messages,
            "temperature": merged_config.temperature,
            "top_p": merged_config.top_p,
        }

        if merged_config.max_tokens:
            kwargs["max_tokens"] = merged_config.max_tokens
        if merged_config.stop:
            kwargs["stop_sequences"] = merged_config.stop
        if merged_config.tools:
            kwargs["tools"] = self._convert_tools(merged_config.tools)
        if merged_config.tool_choice:
            kwargs["tool_choice"] = merged_config.tool_choice
        if merged_config.extra_params:
            kwargs.update(merged_config.extra_params)

        response = await self._client.messages.create(**kwargs)

        content = ""
        tool_calls = None
        for block in response.content:
            if block.type == "text":
                content += block.text
            elif block.type == "tool_use":
                if tool_calls is None:
                    tool_calls = []
                tool_calls.append({
                    "id": block.id,
                    "type": "function",
                    "function": {
                        "name": block.name,
                        "arguments": json.dumps(block.input),
                    },
                })

        return LLMResponse(
            content=content,
            model=response.model,
            usage={
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
            },
            finish_reason=response.stop_reason,
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

        system_prompt = (
            "You must respond with valid JSON that matches the following schema:\n"
            f"{json.dumps(schema, indent=2)}\n\n"
            "Do not include any explanation, only the JSON object."
        )

        new_messages = [LLMMessage(role="system", content=system_prompt)] + messages
        merged_config.response_format = None

        response = await self.generate(new_messages, merged_config)

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
        anthropic_messages = self._convert_messages(messages)

        kwargs = {
            "model": merged_config.model,
            "messages": anthropic_messages,
            "temperature": merged_config.temperature,
            "top_p": merged_config.top_p,
            "stream": True,
        }

        if merged_config.max_tokens:
            kwargs["max_tokens"] = merged_config.max_tokens
        if merged_config.stop:
            kwargs["stop_sequences"] = merged_config.stop
        if merged_config.tools:
            kwargs["tools"] = self._convert_tools(merged_config.tools)
        if merged_config.tool_choice:
            kwargs["tool_choice"] = merged_config.tool_choice
        if merged_config.extra_params:
            kwargs.update(merged_config.extra_params)

        stream = await self._client.messages.create(**kwargs)

        async for chunk in stream:
            if chunk.type == "content_block_delta":
                if chunk.delta.type == "text_delta":
                    yield LLMStreamChunk(
                        content=chunk.delta.text,
                        finish_reason=None,
                    )
            elif chunk.type == "message_delta":
                if chunk.delta.stop_reason:
                    yield LLMStreamChunk(
                        content="",
                        finish_reason=chunk.delta.stop_reason,
                    )

    async def count_tokens(self, messages: List[LLMMessage]) -> int:
        try:
            content = " ".join(m.content for m in messages)
            response = await self._client.messages.count_tokens(
                model=self.config.model,
                messages=[{"role": m.role, "content": m.content} for m in messages if m.role != "system"],
            )
            return response.input_tokens
        except Exception:
            return len(content) // 4