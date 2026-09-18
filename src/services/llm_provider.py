"""
LLM Provider — Abstraction layer for LLM model management.

Supports OpenAI (GPT-4) and provides model switching, fallback chains,
and token usage tracking.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

from langchain_openai import ChatOpenAI

from src.config import get_settings

logger = logging.getLogger(__name__)


def get_llm(
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    **kwargs: Any,
) -> ChatOpenAI:
    """Create and return an LLM instance.

    Args:
        model: Model name override. Defaults to settings.llm_model.
        temperature: Temperature override. Defaults to settings.llm_temperature.
        max_tokens: Max tokens override. Defaults to settings.llm_max_tokens.
        **kwargs: Additional keyword arguments for ChatOpenAI.

    Returns:
        Configured ChatOpenAI instance.
    """
    settings = get_settings()

    llm = ChatOpenAI(
        model=model or settings.llm_model,
        temperature=temperature if temperature is not None else settings.llm_temperature,
        max_tokens=max_tokens or settings.llm_max_tokens,
        api_key=settings.openai_api_key or None,
        **kwargs,
    )

    logger.info(f"LLM initialized: model={model or settings.llm_model}")
    return llm


def get_fallback_llm(**kwargs: Any) -> ChatOpenAI:
    """Get the fallback LLM model (cheaper/faster for non-critical tasks)."""
    settings = get_settings()
    return get_llm(model=settings.llm_fallback_model, **kwargs)


def get_llm_with_fallback(**kwargs: Any) -> Any:
    """Get an LLM with automatic fallback to a cheaper model on failure.

    Uses LangChain's `.with_fallbacks()` to chain primary → fallback.
    """
    primary = get_llm(**kwargs)
    fallback = get_fallback_llm(**kwargs)

    return primary.with_fallbacks([fallback])


class LLMProvider:
    """Managed LLM provider with usage tracking and model switching.

    Provides a clean interface for managing multiple LLM models,
    tracking token usage, and switching between models at runtime.
    """

    def __init__(self) -> None:
        self._settings = get_settings()
        self._primary: ChatOpenAI | None = None
        self._fallback: ChatOpenAI | None = None
        self._total_tokens: int = 0
        self._total_calls: int = 0

    @property
    def primary(self) -> ChatOpenAI:
        if self._primary is None:
            self._primary = get_llm()
        return self._primary

    @property
    def fallback(self) -> ChatOpenAI:
        if self._fallback is None:
            self._fallback = get_fallback_llm()
        return self._fallback

    def get_model(self, model_name: str | None = None) -> ChatOpenAI:
        """Get a specific model by name, or the primary model."""
        if model_name:
            return get_llm(model=model_name)
        return self.primary

    def track_usage(self, tokens: int) -> None:
        """Track token usage."""
        self._total_tokens += tokens
        self._total_calls += 1

    @property
    def usage_stats(self) -> dict[str, int]:
        return {
            "total_tokens": self._total_tokens,
            "total_calls": self._total_calls,
            "avg_tokens_per_call": (
                self._total_tokens // self._total_calls if self._total_calls > 0 else 0
            ),
        }

    def reset_stats(self) -> None:
        self._total_tokens = 0
        self._total_calls = 0


@lru_cache
def get_llm_provider() -> LLMProvider:
    """Return a cached singleton LLM provider."""
    return LLMProvider()
