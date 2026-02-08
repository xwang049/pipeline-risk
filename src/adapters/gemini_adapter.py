"""Google Gemini adapter implementation"""

import time
from typing import List
from loguru import logger

from .base import LLMAdapter, LLMRequest, LLMResponse


class GeminiAdapter(LLMAdapter):
    """
    Google Gemini adapter

    Supports models: gemini-2.5-flash, gemini-2.0-flash, gemini-pro

    Pricing (as of 2024):
    - gemini-2.5-flash: Free tier (20 requests/day), then $0.075/1M tokens
    """

    def __init__(self, config):
        super().__init__(config)

        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self.client = genai
            logger.info(f"Initialized Gemini adapter with model: {self.model}")
        except ImportError:
            raise ImportError(
                "google-generativeai package not installed. "
                "Install with: pip install google-generativeai"
            )
        except Exception as e:
            raise ValueError(f"Failed to initialize Gemini client: {e}")

    def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate completion using Gemini API"""
        start_time = time.time()

        try:
            # Combine system and user prompts for Gemini
            full_prompt = request.prompt
            if request.system_prompt:
                full_prompt = f"{request.system_prompt}\n\n{request.prompt}"

            # Initialize model
            model = self.client.GenerativeModel(
                model_name=self.model,
                generation_config={
                    'temperature': request.temperature,
                    'max_output_tokens': request.max_tokens,
                }
            )

            # Generate
            response = model.generate_content(full_prompt)

            latency = (time.time() - start_time) * 1000

            # Extract text
            text = response.text if hasattr(response, 'text') else str(response)

            # Estimate tokens (Gemini doesn't always provide this)
            tokens_used = len(full_prompt) // 4 + len(text) // 4  # Rough estimate
            cost = self._calculate_cost(tokens_used)

            llm_response = LLMResponse(
                text=text,
                tokens_used=tokens_used,
                latency_ms=latency,
                cost_usd=cost,
                model=self.model,
                provider=self.provider_name,
                metadata={'estimated_tokens': True}
            )

            self._update_statistics(llm_response)
            return llm_response

        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            error_response = LLMResponse(
                text="",
                tokens_used=0,
                latency_ms=(time.time() - start_time) * 1000,
                cost_usd=0.0,
                model=self.model,
                provider=self.provider_name,
                error=str(e)
            )
            self._update_statistics(error_response)
            raise

    def batch_generate(self, requests: List[LLMRequest]) -> List[LLMResponse]:
        """Batch generation for Gemini (sequential)"""
        responses = []
        for request in requests:
            try:
                response = self.generate(request)
                responses.append(response)
            except Exception as e:
                logger.error(f"Batch generation error: {e}")
                error_response = LLMResponse(
                    text="",
                    tokens_used=0,
                    latency_ms=0,
                    cost_usd=0.0,
                    model=self.model,
                    provider=self.provider_name,
                    error=str(e)
                )
                responses.append(error_response)
        return responses

    def _calculate_cost(self, tokens_used: int) -> float:
        """Calculate cost for Gemini"""
        # Free tier: first 20 requests/day
        # Paid: $0.075/1M tokens for Flash models
        cost_per_million = 0.075
        return (tokens_used / 1_000_000) * cost_per_million

    @property
    def provider_name(self) -> str:
        return "gemini"
