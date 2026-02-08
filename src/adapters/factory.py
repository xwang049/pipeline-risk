"""LLM adapter factory"""

from typing import Dict, Any
from loguru import logger

from .base import LLMAdapter
from .openai_adapter import OpenAIAdapter
from .gemini_adapter import GeminiAdapter


class AdapterFactory:
    """
    Factory for creating LLM adapters

    Provides centralized adapter creation with validation.
    Easy to extend with new providers.
    """

    _adapters = {
        "openai": OpenAIAdapter,
        "gemini": GeminiAdapter,
    }

    @classmethod
    def create(cls, provider: str, config: Dict[str, Any]) -> LLMAdapter:
        """
        Create an LLM adapter

        Args:
            provider: Provider name (openai, anthropic, gemini)
            config: Configuration dictionary

        Returns:
            LLMAdapter instance

        Raises:
            ValueError: If provider is unknown
        """
        if provider not in cls._adapters:
            raise ValueError(
                f"Unknown LLM provider: '{provider}'. "
                f"Available providers: {list(cls._adapters.keys())}"
            )

        adapter_class = cls._adapters[provider]

        try:
            adapter = adapter_class(config)
            logger.info(f"Created {provider} adapter: {adapter.model}")
            return adapter
        except Exception as e:
            logger.error(f"Failed to create {provider} adapter: {e}")
            raise

    @classmethod
    def register(cls, provider: str, adapter_class: type):
        """
        Register a new adapter class

        Args:
            provider: Provider name
            adapter_class: LLMAdapter subclass
        """
        cls._adapters[provider] = adapter_class
        logger.info(f"Registered adapter: {provider}")

    @classmethod
    def list_providers(cls) -> list:
        """List all registered providers"""
        return list(cls._adapters.keys())
