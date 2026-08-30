import json
import logging
from typing import Any, AsyncIterator, Dict, List, Optional, Type, TypeVar

from backend.providers.llm.base import (
    LLMConfig, LLMMessage, LLMProvider, LLMProviderType, LLMResponse, LLMStreamChunk
)

logger = logging.getLogger(__name__)

T = TypeVar('T')


class GoogleProvider(LLMProvider):
    """Google Gemini LLM provider implementation."""

    def __init__(self, config: LLMConfig, api_key: str):
        super().__init__(config)
        self.api_key = api_key

    @property
    def provider_type(self) -> LLMProviderType:
        return LLMProviderType.GOOGLE

    async def initialize(self) -> None:
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self._client = genai
            self._model = genai.GenerativeModel(self.config.model)
            logger.info("Google provider initialized")
        except ImportError:
            raise ImportError("google-generativeai package not installed. Run: pip install google-generativeai")

    async def close(self) -> None:
        self._client = None
        self._model = None

    def _convert_messages(self, messages: List[LLMMessage]) -> List[Dict[str, Any]]:
        """Convert LLMMessage to Google format."""
        converted = []
        for msg in messages:
            role = "user" if msg.role == "user" else "model" if msg.role == "assistant" else msg.role
            converted.append({
                "role": role,
                "parts": [{"text": msg.content}],
            })
        return converted

    async def generate(
        self,
        messages: List[LLMMessage],
        config: Optional[LLMConfig] = None,
    ) -> LLMResponse:
        merged_config = self._merge_config(config)
        google_messages = self._convert_messages(messages)

        generation_config = {
            "temperature": merged_config.temperature,
            "top_p": merged_config.top_p,
        }
        if merged_config.max_tokens:
            generation_config["max_output_tokens"] = merged_config.max_tokens
        if merged_config.stop:
            generation_config["stop_sequences"] = merged_config.stop

        response = await self._model.generate_content_async(
            google_messages,
            generation_config=generation_config,
        )

        return LLMResponse(
            content=response.text or "",
            model=merged_config.model,
            usage={
                "prompt_tokens": response.usage_metadata.prompt_token_count if hasattr(response, 'usage_metadata') else 0,
                "completion_tokens": response.usage_metadata.candidates_token_count if hasattr(response, 'usage_metadata') else 0,
                "total_tokens": response.usage_metadata.total_token_count if hasattr(response, 'usage_metadata') else 0,
            },
            finish_reason=response.candidates[0].finish_reason.name if response.candidates else "STOP",
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

        new_messages = [LLMMessage(role="user", content=system_prompt)] + messages

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
        google_messages = self._convert_messages(messages)

        generation_config = {
            "temperature": merged_config.temperature,
            "top_p": merged_config.top_p,
        }
        if merged_config.max_tokens:
            generation_config["max_output_tokens"] = merged_config.max_tokens
        if merged_config.stop:
            generation_config["stop_sequences"] = merged_config.stop

        stream = await self._model.generate_content_async(
            google_messages,
            generation_config=generation_config,
            stream=True,
        )

        async for chunk in stream:
            if chunk.text:
                yield LLMStreamChunk(
                    content=chunk.text,
                    finish_reason=None,
                )

    async def count_tokens(self, messages: List[LLMMessage]) -> int:
        try:
            google_messages = self._convert_messages(messages)
            response = await self._model.count_tokens_async(google_messages)
            return response.total_tokens
        except Exception:
            content = " ".join(m.content for m in messages)
            return len(content) // 4