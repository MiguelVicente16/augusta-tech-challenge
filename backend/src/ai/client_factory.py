"""
AI Client Factory - Unified interface for multiple AI providers

Supports:
- OpenAI (GPT-5-mini)
- Google Gemini (Gemini 2.0 Flash)
"""

import logging
import os
from enum import Enum
from typing import Optional

from .openai_client import OpenAIClient, StructuredDescriptionGenerator as OpenAIGenerator
from .gemini_client import GeminiClient, StructuredDescriptionGenerator as GeminiGenerator
from ..config import get_settings

logger = logging.getLogger(__name__)


class AIProvider(str, Enum):
    """Supported AI providers"""
    OPENAI = "openai"
    GEMINI = "gemini"


class AIClientFactory:
    """
    Factory for creating AI clients with unified interface.

    Supports redundancy - if one provider fails, can fallback to another.
    """

    @staticmethod
    def create_client(
        provider: str = "openai",
        api_key: Optional[str] = None,
        model: Optional[str] = None
    ):
        """
        Create AI client for specified provider

        Args:
            provider: Provider name ("openai" or "gemini")
            api_key: API key (optional, reads from env if not provided)
            model: Model name (optional, uses default if not provided)

        Returns:
            Client instance (OpenAIClient or GeminiClient)

        Raises:
            ValueError: If provider is not supported
        """
        provider = provider.lower()
        settings = get_settings()

        if provider == AIProvider.OPENAI:
            default_model = model or os.getenv("OPENAI_MODEL", "gpt-5-mini")
            request_delay = settings.AI_REQUEST_DELAY_SECONDS
            logger.info(f"Creating OpenAI client with model: {default_model}, delay: {request_delay}s")
            return OpenAIClient(api_key=api_key, model=default_model, request_delay=request_delay)

        elif provider == AIProvider.GEMINI:
            try:
                from .gemini_client import GeminiClient
                default_model = model or os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
                request_delay = settings.AI_REQUEST_DELAY_SECONDS
                logger.info(f"Creating Gemini client with model: {default_model}, delay: {request_delay}s")
                return GeminiClient(api_key=api_key, model=default_model, request_delay=request_delay)
            except ImportError as e:
                raise ValueError(
                    f"Gemini client not available. Missing dependency: {e}. "
                    f"Install with: pip install google-generativeai"
                )

        else:
            raise ValueError(
                f"Unsupported provider: {provider}. "
                f"Must be one of: {[p.value for p in AIProvider]}"
            )

    @staticmethod
    def create_generator(
        provider: str = "openai",
        api_key: Optional[str] = None,
        model: Optional[str] = None
    ):
        """
        Create StructuredDescriptionGenerator for specified provider

        Args:
            provider: Provider name ("openai" or "gemini")
            api_key: API key (optional, reads from env if not provided)
            model: Model name (optional, uses default if not provided)

        Returns:
            StructuredDescriptionGenerator instance
        """
        client = AIClientFactory.create_client(provider, api_key, model)

        if provider.lower() == AIProvider.OPENAI:
            return OpenAIGenerator(client)
        elif provider.lower() == AIProvider.GEMINI:
            try:
                from .gemini_client import StructuredDescriptionGenerator as GeminiGenerator
                return GeminiGenerator(client)
            except ImportError as e:
                raise ValueError(
                    f"Gemini client not available. Missing dependency: {e}. "
                    f"Install with: pip install google-generativeai"
                )
        else:
            raise ValueError(f"Unsupported provider: {provider}")


class RedundantAIClient:
    """
    AI client with automatic fallback support.

    Tries primary provider first, falls back to secondary if primary fails.
    Useful for production reliability.
    """

    def __init__(
        self,
        primary_provider: str = "openai",
        secondary_provider: str = "gemini",
        primary_api_key: Optional[str] = None,
        secondary_api_key: Optional[str] = None
    ):
        """
        Initialize redundant client with fallback

        Args:
            primary_provider: Primary provider to use
            secondary_provider: Fallback provider if primary fails
            primary_api_key: API key for primary provider
            secondary_api_key: API key for secondary provider
        """
        self.primary_provider = primary_provider
        self.secondary_provider = secondary_provider

        # Try to initialize both clients
        self.primary_client = None
        self.secondary_client = None

        try:
            self.primary_client = AIClientFactory.create_client(
                primary_provider,
                api_key=primary_api_key
            )
            logger.info(f"Primary AI provider initialized: {primary_provider}")
        except Exception as e:
            logger.warning(f"Failed to initialize primary provider {primary_provider}: {e}")

        try:
            self.secondary_client = AIClientFactory.create_client(
                secondary_provider,
                api_key=secondary_api_key
            )
            logger.info(f"Secondary AI provider initialized: {secondary_provider}")
        except Exception as e:
            logger.warning(f"Failed to initialize secondary provider {secondary_provider}: {e}")

        if not self.primary_client and not self.secondary_client:
            raise RuntimeError("Failed to initialize any AI provider")

    def complete(self, *args, **kwargs):
        """
        Complete with automatic fallback

        Tries primary provider first, falls back to secondary if it fails.
        """
        # Try primary
        if self.primary_client:
            try:
                return self.primary_client.complete(*args, **kwargs)
            except Exception as e:
                logger.error(f"Primary provider {self.primary_provider} failed: {e}")
                logger.info("Attempting fallback to secondary provider...")

        # Fallback to secondary
        if self.secondary_client:
            try:
                return self.secondary_client.complete(*args, **kwargs)
            except Exception as e:
                logger.error(f"Secondary provider {self.secondary_provider} failed: {e}")
                raise

        raise RuntimeError("All AI providers failed")

    def get_usage_summary(self) -> str:
        """Get combined usage summary from all providers"""
        summaries = []
        if self.primary_client:
            summaries.append(f"{self.primary_provider}: {self.primary_client.get_usage_summary()}")
        if self.secondary_client:
            summaries.append(f"{self.secondary_provider}: {self.secondary_client.get_usage_summary()}")
        return " | ".join(summaries)
