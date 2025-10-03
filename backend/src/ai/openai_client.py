"""OpenAI client for generating structured descriptions with cost tracking"""

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

from openai import OpenAI

from .prompts import (
    STRUCTURED_DESCRIPTION_SYSTEM_PROMPT,
    STRUCTURED_DESCRIPTION_USER_PROMPT
)

logger = logging.getLogger(__name__)


@dataclass
class UsageMetrics:
    """Track API usage and costs"""
    total_calls: int = 0
    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_cost: float = 0.0

    def add_call(self, prompt_tokens: int, completion_tokens: int, cost: float):
        """Add metrics from a single API call"""
        self.total_calls += 1
        self.prompt_tokens += prompt_tokens
        self.completion_tokens += completion_tokens
        self.total_tokens += prompt_tokens + completion_tokens
        self.total_cost += cost

    def __str__(self) -> str:
        return (
            f"API Calls: {self.total_calls} | "
            f"Tokens: {self.total_tokens:,} "
            f"(prompt: {self.prompt_tokens:,}, completion: {self.completion_tokens:,}) | "
            f"Cost: ${self.total_cost:.4f}"
        )


class OpenAIClient:
    """
    OpenAI client with cost tracking and flexible prompt support.
    Uses GPT-5-mini for cost-efficient operations.
    """

    # Pricing per 1M tokens (as of 2024)
    PRICING = {
        "gpt-4.1-mini": {
            "prompt": 0.15,      # $0.15 per 1M prompt tokens
            "completion": 0.60    # $0.60 per 1M completion tokens
        },
        "gpt-5-mini": {
            "prompt": 0.10,      # $0.10 per 1M prompt tokens (estimated)
            "completion": 0.40    # $0.40 per 1M completion tokens (estimated)
        }
    }

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-5-mini", request_delay: float = 6.0):
        """
        Initialize OpenAI client with cost tracking and rate limiting

        Args:
            api_key: OpenAI API key. If None, reads from OPENAI_API_KEY env var
            model: Model to use (default: gpt-5-mini for cost efficiency)
            request_delay: Minimum delay between requests in seconds (default: 6.0)
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key not provided. Set OPENAI_API_KEY env var.")

        self.client = OpenAI(api_key=self.api_key)
        self.model = model
        self.usage = UsageMetrics()
        self.request_delay = request_delay
        self.last_request_time = 0.0

        logger.info(f"OpenAI client initialized with model: {self.model}")

    def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 500,
        response_format: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Generic completion method with cost tracking

        Args:
            prompt: User prompt
            system_prompt: System prompt (optional)
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Maximum tokens in response
            response_format: Response format, e.g., {"type": "json_object"} for JSON mode

        Returns:
            Dict with 'content' (response text) and 'usage' (token metrics)
        """
        # Rate limiting: ensure minimum delay between requests
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.request_delay:
            sleep_time = self.request_delay - time_since_last_request
            logger.info(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature
                # "max_tokens": max_tokens
            }

            # Add response_format if specified (for JSON mode)
            if response_format:
                kwargs["response_format"] = response_format

            # Update last request time before making the request
            self.last_request_time = time.time()
            
            response = self.client.chat.completions.create(**kwargs)

            # Extract usage metrics
            usage = response.usage
            cost = self._calculate_cost(usage.prompt_tokens, usage.completion_tokens)

            # Track usage
            self.usage.add_call(usage.prompt_tokens, usage.completion_tokens, cost)

            # Log usage for this call
            logger.info(
                f"API call completed | "
                f"Tokens: {usage.total_tokens} "
                f"(prompt: {usage.prompt_tokens}, completion: {usage.completion_tokens}) | "
                f"Cost: ${cost:.4f}"
            )

            return {
                "content": response.choices[0].message.content,
                "usage": {
                    "prompt_tokens": usage.prompt_tokens,
                    "completion_tokens": usage.completion_tokens,
                    "total_tokens": usage.total_tokens,
                    "cost": cost
                }
            }

        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise

    def _calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Calculate cost based on token usage"""
        pricing = self.PRICING.get(self.model, self.PRICING["gpt-4.1-mini"])

        prompt_cost = (prompt_tokens / 1_000_000) * pricing["prompt"]
        completion_cost = (completion_tokens / 1_000_000) * pricing["completion"]

        return prompt_cost + completion_cost

    def get_usage_summary(self) -> str:
        """Get formatted usage summary"""
        return str(self.usage)

    def reset_usage(self):
        """Reset usage metrics"""
        self.usage = UsageMetrics()
        logger.info("Usage metrics reset")


class StructuredDescriptionGenerator:
    """Generate structured JSON descriptions from plain text incentive descriptions"""

    def __init__(self, client: OpenAIClient):
        """
        Initialize generator with OpenAI client

        Args:
            client: OpenAIClient instance
        """
        self.client = client

    def generate(
        self,
        title: str,
        description: Optional[str] = None,
        ai_description: Optional[str] = None,
        custom_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate structured JSON description from incentive text

        Args:
            title: Incentive title
            description: Original description (optional)
            ai_description: AI-generated description from CSV (optional)
            custom_prompt: Custom extraction prompt (optional, overrides default)

        Returns:
            Structured JSON with key information extracted
        """
        # Build input text from available fields
        input_parts = [f"Title: {title}"]
        if description:
            input_parts.append(f"Description: {description}")
        if ai_description:
            input_parts.append(f"AI Description: {ai_description}")

        input_text = "\n\n".join(input_parts)

        # Use custom prompt or default from prompts.py
        if custom_prompt:
            prompt = custom_prompt
            system_prompt = STRUCTURED_DESCRIPTION_SYSTEM_PROMPT
        else:
            prompt = STRUCTURED_DESCRIPTION_USER_PROMPT.format(input_text=input_text)
            system_prompt = STRUCTURED_DESCRIPTION_SYSTEM_PROMPT

        try:
            result = self.client.complete(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.1,
                max_tokens=500
            )

            # Parse JSON response
            structured_data = json.loads(result["content"].strip())

            logger.info(f"Successfully generated structured description for: {title}")
            return structured_data

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Response was: {result.get('content', 'N/A')}")
            return self._get_default_structure()

        except Exception as e:
            logger.error(f"Error generating structured description: {e}")
            return self._get_default_structure()

    def _get_default_structure(self) -> Dict[str, Any]:
        """Return default empty structure when generation fails"""
        return {
            "objective": "",
            "target_sectors": [],
            "target_regions": [],
            "eligible_activities": [],
            "funding_type": "other",
            "key_requirements": [],
            "innovation_focus": False,
            "sustainability_focus": False,
            "digital_transformation_focus": False
        }
