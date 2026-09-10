"""LLM-backed generator for Career-to-Content drafts.

Resolves a provider through the existing ``backend.providers.llm`` factory
(default provider when configured, otherwise the Mock provider so the
pipeline stays operable in dev/test without API keys).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from backend.content_engine.generation import career_templates
from backend.models.content_pipeline_run import ContentKind
from backend.providers.llm.base import LLMConfig, LLMMessage
from backend.providers.llm.factory import get_llm_factory
from backend.providers.llm.base import LLMProviderType
from backend.providers.llm.mock import MockProvider

logger = logging.getLogger(__name__)


class CareerContentGenerator:
    """Generate career-grounded content drafts with an LLM provider."""

    def __init__(self, provider=None, model: str = "gpt-4o-mini", temperature: float = 0.7):
        self._provider = provider
        self._model = model
        self._temperature = temperature

    def _resolve_provider(self):
        if self._provider is not None:
            return self._provider
        # Prefer a real, keyed provider; otherwise stay operable offline
        # via Mock so dev/test pipelines don't fail for missing API keys.
        try:
            from backend.providers.config import load_llm_settings

            settings = load_llm_settings()
            default = settings.default_provider
            entry = settings.providers.get(default)
            needs_key = default not in (LLMProviderType.MOCK, LLMProviderType.OLLAMA)
            if entry is not None and (not needs_key or getattr(entry, "api_key", None)):
                config = LLMConfig(
                    model=getattr(entry, "model", None) or self._model,
                    temperature=self._temperature,
                )
                return get_llm_factory().create(default, config)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("LLM provider resolution failed (%s); using Mock provider", exc)
        return MockProvider(LLMConfig(model="mock", temperature=self._temperature))

    async def generate(self, content_kind: ContentKind, brief: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a draft; returns {text, model, kind}."""
        system, user = career_templates.build_prompt(content_kind, brief)
        provider = self._resolve_provider()
        try:
            response = await provider.generate(
                [LLMMessage(role="system", content=system), LLMMessage(role="user", content=user)]
            )
            text, model = response.content, response.model
        finally:
            try:
                await provider.close()
            except Exception:  # pragma: no cover - defensive
                pass
        return {"text": text or "", "model": model, "kind": content_kind.value}
