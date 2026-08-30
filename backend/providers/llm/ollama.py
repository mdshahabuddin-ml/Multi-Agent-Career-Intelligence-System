import json
import logging
from typing import Any, AsyncIterator, Dict, List, Optional, Type, TypeVar

import httpx

from backend.providers.llm.base import (
    LLMConfig, LLMMessage, LLMProvider, LLMProviderType, LLMResponse, LLMStreamChunk
)

logger = logging.getLogger(__name__)

T = TypeVar('T')


class OllamaProvider(LLMProvider):
    """Ollama local LLM provider implementation."""

    def __init__(self, config: LLMConfig, base_url: str = "http://localhost:11434"):
        super().__init__(config)
        self.base_url = base_url.rstrip("/")
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def provider_type(self) -> LLMProviderType:
        return LLMProviderType.OLLAMA

    async def initialize(self) -> None:
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=120.0)
        try:
            await self._client.get("/api/tags")
            logger.info(f"Ollama provider initialized at {self.base_url}")
        except Exception as e:
            logger.error(f"Failed to connect to Ollama: {e}")
            raise

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    def _convert_messages(self, messages: List[LLMMessage]) -> List[Dict[str, Any]]:
        """Convert LLMMessage to Ollama format."""
        return [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]

    def _build_options(self, config: LLMConfig) -> Dict[str, Any]:
        """Build Ollama options from config."""
        options = {}
        if config.temperature is not None:
            options["temperature"] = config.temperature
        if config.top_p is not None:
            options["top_p"] = config.top_p
        if config.max_tokens is not None:
            options["num_predict"] = config.max_tokens
        if config.stop:
            options["stop"] = config.stop
        if config.extra_params:
            options.update(config.extra_params)
        return options

    async def generate(
        self,
        messages: List[LLMMessage],
        config: Optional[LLMConfig] = None,
    ) -> LLMResponse:
        merged_config = self._merge_config(config)
        ollama_messages = self._convert_messages(messages)
        options = self._build_options(merged_config)

        payload = {
            "model": merged_config.model,
            "messages": ollama_messages,
            "stream": False,
            "options": options,
        }

        if merged_config.response_format:
            payload["format"] = merged_config.response_format.get("type", "json")

        response = await self._client.post("/api/chat", json=payload)
        response.raise_for_status()
        data = response.json()

        return LLMResponse(
            content=data.get("message", {}).get("content", ""),
            model=data.get("model", merged_config.model),
            usage={
                "prompt_tokens": data.get("prompt_eval_count", 0),
                "completion_tokens": data.get("eval_count", 0),
                "total_tokens": data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
            },
            finish_reason=data.get("done_reason", "stop"),
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
        merged_config.response_format = {"type": "json"}

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
        ollama_messages = self._convert_messages(messages)
        options = self._build_options(merged_config)

        payload = {
            "model": merged_config.model,
            "messages": ollama_messages,
            "stream": True,
            "options": options,
        }

        async with self._client.stream("POST", "/api/chat", json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    if "message" in data and "content" in data["message"]:
                        content = data["message"]["content"]
                        if content:
                            yield LLMStreamChunk(
                                content=content,
                                finish_reason=data.get("done_reason") if data.get("done") else None,
                            )
                except json.JSONDecodeError:
                    continue

    async def count_tokens(self, messages: List[LLMMessage]) -> int:
        content = " ".join(m.content for m in messages)
        return len(content) // 4

    async def list_models(self) -> List[str]:
        """List available models."""
        response = await self._client.get("/api/tags")
        response.raise_for_status()
        data = response.json()
        return [model["name"] for model in data.get("models", [])]

    async def pull_model(self, model_name: str) -> AsyncIterator[Dict[str, Any]]:
        """Pull a model."""
        async with self._client.stream("POST", "/api/pull", json={"name": model_name}) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line:
                    yield json.loads(line)