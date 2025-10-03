"""Google Gemini client for generating structured descriptions with cost tracking"""

import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

import google.generativeai as genai

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


class GeminiClient:
    """
    Google Gemini client with cost tracking and flexible prompt support.
    Uses Gemini 2.0 Flash for cost-efficient operations.
    """

    # Pricing per 1M tokens (as of 2024)
    PRICING = {
        "gemini-1.5-flash": {
            "prompt": 0.075,      # $0.075 per 1M prompt tokens
            "completion": 0.30    # $0.30 per 1M completion tokens
        },
        "gemini-1.5-flash-8b": {
            "prompt": 0.0375,     # $0.0375 per 1M prompt tokens (even cheaper)
            "completion": 0.15    # $0.15 per 1M completion tokens
        },
        "gemini-2.0-flash": {
            "prompt": 0.05,       # $0.05 per 1M prompt tokens (estimated)
            "completion": 0.20    # $0.20 per 1M completion tokens (estimated)
        }
    }

    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-2.0-flash", request_delay: float = 6.0):
        """
        Initialize Gemini client with cost tracking and rate limiting

        Args:
            api_key: Google API key. If None, reads from GEMINI_API_KEY env var
            model: Model to use (default: gemini-2.0-flash for cost efficiency)
            request_delay: Minimum delay between requests in seconds (default: 6.0)
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("Gemini API key not provided. Set GEMINI_API_KEY env var.")

        genai.configure(api_key=self.api_key)
        self.model_name = model
        self.request_delay = request_delay
        self.last_request_time = 0.0
        self.model = genai.GenerativeModel(model)
        self.usage = UsageMetrics()

        logger.info(f"Gemini client initialized with model: {self.model_name}")

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
            response_format: Response format (for compatibility, Gemini uses JSON mode differently)

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
        
        # Combine system and user prompts for Gemini
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"

        # For JSON output, add explicit instruction
        if response_format and response_format.get("type") == "json_object":
            full_prompt += "\n\nRespond with valid JSON only, no markdown formatting."

        try:
            generation_config = {
                "temperature": temperature,
                "max_output_tokens": max_tokens,
            }

            # Update last request time before making the request
            self.last_request_time = time.time()

            response = self.model.generate_content(
                full_prompt,
                generation_config=generation_config
            )

            # Extract usage metrics with fallback for different API versions
            try:
                if hasattr(response, 'usage_metadata') and response.usage_metadata:
                    usage_metadata = response.usage_metadata
                    prompt_tokens = getattr(usage_metadata, 'prompt_token_count', 0)
                    completion_tokens = getattr(usage_metadata, 'candidates_token_count', 0)
                    total_tokens = getattr(usage_metadata, 'total_token_count', prompt_tokens + completion_tokens)
                else:
                    # Fallback: estimate tokens if usage_metadata is not available
                    prompt_tokens = len(full_prompt.split()) * 1.3  # Rough estimate
                    completion_tokens = len(response.text.split()) * 1.3 if response.text else 0
                    total_tokens = int(prompt_tokens + completion_tokens)
                    prompt_tokens = int(prompt_tokens)
                    completion_tokens = int(completion_tokens)
                    logger.warning("Usage metadata not available, using estimated token counts")
            except (AttributeError, TypeError) as e:
                # Fallback: estimate tokens if usage_metadata access fails
                prompt_tokens = len(full_prompt.split()) * 1.3  # Rough estimate
                completion_tokens = len(response.text.split()) * 1.3 if response.text else 0
                total_tokens = int(prompt_tokens + completion_tokens)
                prompt_tokens = int(prompt_tokens)
                completion_tokens = int(completion_tokens)
                logger.warning(f"Could not access usage metadata: {e}. Using estimated token counts")

            # Calculate cost
            cost = self._calculate_cost(prompt_tokens, completion_tokens)

            # Track usage
            self.usage.add_call(prompt_tokens, completion_tokens, cost)

            # Log usage for this call
            logger.info(
                f"API call completed | "
                f"Tokens: {total_tokens} "
                f"(prompt: {prompt_tokens}, completion: {completion_tokens}) | "
                f"Cost: ${cost:.4f}"
            )

            return {
                "content": response.text,
                "usage": {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": total_tokens,
                    "cost": cost
                }
            }

        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            raise

    def _calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Calculate cost based on token usage"""
        pricing = self.PRICING.get(self.model_name, self.PRICING["gemini-1.5-flash"])

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

    def __init__(self, client: GeminiClient):
        """
        Initialize generator with Gemini client

        Args:
            client: GeminiClient instance
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
                max_tokens=500,
                response_format={"type": "json_object"}
            )

            # Parse JSON response
            content = result["content"].strip()
            # Remove markdown code blocks if present
            if content.startswith("```json"):
                content = content.replace("```json", "").replace("```", "").strip()
            elif content.startswith("```"):
                content = content.replace("```", "").strip()

            structured_data = json.loads(content)

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
