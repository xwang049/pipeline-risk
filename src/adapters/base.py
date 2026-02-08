"""LLM adapter base classes and interfaces"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class LLMRequest:
    """
    Request to LLM (inspired by HELM's Request)

    Immutable request object that encapsulates all information
    needed to make an LLM API call.
    """
    prompt: str
    system_prompt: Optional[str] = None
    temperature: float = 0.1
    max_tokens: int = 2000
    stop_sequences: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate request parameters"""
        if self.temperature < 0 or self.temperature > 2:
            raise ValueError("Temperature must be between 0 and 2")
        if self.max_tokens <= 0:
            raise ValueError("max_tokens must be positive")


@dataclass
class LLMResponse:
    """
    Response from LLM (inspired by HELM's RequestResult)

    Immutable response object that includes generated text,
    usage metrics, and cost tracking.
    """
    text: str
    tokens_used: int
    latency_ms: float
    cost_usd: float
    model: str
    provider: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        """Check if response was successful"""
        return self.error is None

    def __post_init__(self):
        """Ensure immutability"""
        object.__setattr__(self, 'metadata', dict(self.metadata))


class LLMAdapter(ABC):
    """
    Abstract LLM adapter (Strategy pattern)

    Design philosophy:
    - Unified interface across providers
    - Track costs and latency
    - Support batch generation for efficiency
    - Handle errors gracefully

    Implementations:
        - OpenAIAdapter: OpenAI GPT models
        - AnthropicAdapter: Claude models
        - GeminiAdapter: Google Gemini models
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize LLM adapter

        Args:
            config: Configuration dictionary containing:
                - model: Model identifier
                - api_key: API key for authentication
                - temperature: Default temperature
                - max_tokens: Default max tokens
                - Any provider-specific settings
        """
        self.config = config
        self.model = config['model']
        self.api_key = config.get('api_key')
        self.default_temperature = config.get('temperature', 0.1)
        self.default_max_tokens = config.get('max_tokens', 2000)

        # Statistics
        self.total_tokens_used = 0
        self.total_cost_usd = 0.0
        self.total_requests = 0
        self.failed_requests = 0

    @abstractmethod
    def generate(self, request: LLMRequest) -> LLMResponse:
        """
        Generate completion from the LLM

        Args:
            request: LLMRequest object with prompt and parameters

        Returns:
            LLMResponse object with generated text and metrics

        Raises:
            Exception: If API call fails after retries
        """
        pass

    @abstractmethod
    def batch_generate(self, requests: List[LLMRequest]) -> List[LLMResponse]:
        """
        Generate completions for multiple requests (batch processing)

        Args:
            requests: List of LLMRequest objects

        Returns:
            List of LLMResponse objects

        Note:
            Some providers support true batch APIs (more efficient).
            Default implementation just calls generate() in a loop.
        """
        pass

    @abstractmethod
    def _calculate_cost(self, tokens_used: int) -> float:
        """
        Calculate cost in USD for token usage

        Args:
            tokens_used: Total tokens (prompt + completion)

        Returns:
            Cost in USD

        Note:
            Each provider has different pricing.
            Subclasses must implement based on their model pricing.
        """
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """
        Return provider name

        Returns:
            Provider identifier (e.g., "openai", "anthropic", "gemini")
        """
        pass

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get usage statistics

        Returns:
            Dictionary with:
                - total_requests: Number of requests made
                - failed_requests: Number of failed requests
                - total_tokens_used: Total tokens consumed
                - total_cost_usd: Total cost in USD
                - average_tokens_per_request: Average tokens per request
        """
        avg_tokens = (
            self.total_tokens_used / self.total_requests
            if self.total_requests > 0
            else 0
        )

        return {
            'provider': self.provider_name,
            'model': self.model,
            'total_requests': self.total_requests,
            'failed_requests': self.failed_requests,
            'success_rate': (
                (self.total_requests - self.failed_requests) / self.total_requests
                if self.total_requests > 0
                else 0
            ),
            'total_tokens_used': self.total_tokens_used,
            'total_cost_usd': round(self.total_cost_usd, 4),
            'average_tokens_per_request': round(avg_tokens, 1),
        }

    def _update_statistics(self, response: LLMResponse):
        """Update internal statistics after each request"""
        self.total_requests += 1
        if response.success:
            self.total_tokens_used += response.tokens_used
            self.total_cost_usd += response.cost_usd
        else:
            self.failed_requests += 1

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"provider={self.provider_name}, "
            f"model={self.model}, "
            f"requests={self.total_requests}, "
            f"cost=${self.total_cost_usd:.4f})"
        )
