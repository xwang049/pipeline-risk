"""OpenAI adapter implementation"""

import time
from typing import List
from loguru import logger

from .base import LLMAdapter, LLMRequest, LLMResponse


class OpenAIAdapter(LLMAdapter):
    """
    OpenAI GPT adapter

    Supports models: gpt-4o, gpt-4o-mini, gpt-4-turbo, etc.

    Pricing (as of 2024):
    - gpt-4o-mini: $0.15/1M input, $0.60/1M output tokens
    - gpt-4o: $5/1M input, $15/1M output tokens
    """

    def __init__(self, config):
        super().__init__(config)

        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=self.api_key)
            logger.info(f"Initialized OpenAI adapter with model: {self.model}")
        except ImportError:
            raise ImportError(
                "openai package not installed. "
                "Install with: pip install openai"
            )
        except Exception as e:
            raise ValueError(f"Failed to initialize OpenAI client: {e}")

    def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate completion using OpenAI API"""
        start_time = time.time()

        try:
            # Build messages
            messages = []
            if request.system_prompt:
                messages.append({"role": "system", "content": request.system_prompt})
            messages.append({"role": "user", "content": request.prompt})

            # Make API call
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                stop=request.stop_sequences if request.stop_sequences else None,
            )

            latency = (time.time() - start_time) * 1000
            tokens_used = response.usage.total_tokens
            cost = self._calculate_cost(tokens_used)

            llm_response = LLMResponse(
                text=response.choices[0].message.content,
                tokens_used=tokens_used,
                latency_ms=latency,
                cost_usd=cost,
                model=self.model,
                provider=self.provider_name,
                metadata={
                    'finish_reason': response.choices[0].finish_reason,
                    'prompt_tokens': response.usage.prompt_tokens,
                    'completion_tokens': response.usage.completion_tokens,
                }
            )

            self._update_statistics(llm_response)
            return llm_response

        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
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
        """
        Batch generation for OpenAI

        Note: OpenAI doesn't have a true batch API for chat completions,
        so we just call generate() sequentially.
        """
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
        """
        Calculate cost based on OpenAI pricing

        Simplified: Assumes 50/50 split between input/output tokens
        """
        # Model pricing (per 1M tokens)
        pricing = {
            'gpt-4o-mini': {'input': 0.15, 'output': 0.60},
            'gpt-4o': {'input': 5.00, 'output': 15.00},
            'gpt-4-turbo': {'input': 10.00, 'output': 30.00},
            'gpt-4': {'input': 30.00, 'output': 60.00},
        }

        # Default pricing if model not found
        default_pricing = {'input': 0.15, 'output': 0.60}

        # Get pricing for this model
        model_pricing = pricing.get(self.model, default_pricing)

        # Simplified: assume 50/50 split (actual split available in response.usage)
        input_tokens = tokens_used * 0.5
        output_tokens = tokens_used * 0.5

        cost = (
            (input_tokens / 1_000_000) * model_pricing['input'] +
            (output_tokens / 1_000_000) * model_pricing['output']
        )

        return cost

    @property
    def provider_name(self) -> str:
        return "openai"
