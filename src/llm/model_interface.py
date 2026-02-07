"""LLM model interface for multiple providers"""

import os
import json
from typing import Dict, Any, Optional
from loguru import logger
from dotenv import load_dotenv

load_dotenv()


class LLMInterface:
    """Unified interface for different LLM providers"""

    def __init__(
        self,
        provider: str = "openai",
        model: str = None,
        temperature: float = 0.1,
        max_tokens: int = 2000,
    ):
        """
        Initialize LLM interface

        Args:
            provider: LLM provider (openai, anthropic, local)
            model: Model name
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
        """
        self.provider = provider.lower()
        self.temperature = temperature
        self.max_tokens = max_tokens

        # Set default models (using cost-effective options)
        if model is None:
            if self.provider == "openai":
                self.model = "gpt-4o-mini"  # Cheaper than GPT-4 (~$0.15/1M tokens)
            elif self.provider == "anthropic":
                self.model = "claude-3-5-haiku-20241022"  # Cheapest Claude (~$1/1M tokens)
            elif self.provider == "gemini":
                self.model = "models/gemini-2.5-flash"  # Fast and free in quota
            else:
                self.model = "default"
        else:
            self.model = model

        # Initialize the appropriate client
        self._init_client()

        logger.info(
            f"Initialized LLM interface: provider={self.provider}, model={self.model}"
        )

    def _init_client(self):
        """Initialize the client based on provider"""
        if self.provider == "openai":
            try:
                from openai import OpenAI

                api_key = os.getenv("OPENAI_API_KEY")
                if not api_key:
                    raise ValueError(
                        "OPENAI_API_KEY not found in environment variables"
                    )
                self.client = OpenAI(api_key=api_key)
            except ImportError:
                raise ImportError("openai package not installed")

        elif self.provider == "anthropic":
            try:
                from anthropic import Anthropic

                api_key = os.getenv("ANTHROPIC_API_KEY")
                if not api_key:
                    raise ValueError(
                        "ANTHROPIC_API_KEY not found in environment variables"
                    )
                self.client = Anthropic(api_key=api_key)
            except ImportError:
                raise ImportError("anthropic package not installed")

        elif self.provider == "gemini":
            try:
                import google.generativeai as genai

                api_key = os.getenv("GEMINI_API_KEY")
                if not api_key:
                    raise ValueError(
                        "GEMINI_API_KEY not found in environment variables"
                    )
                genai.configure(api_key=api_key)
                self.client = genai
            except ImportError:
                raise ImportError("google-generativeai package not installed")

        elif self.provider == "local":
            # For local models (e.g., via Ollama or vLLM)
            logger.warning("Local model support not yet implemented")
            self.client = None

        else:
            raise ValueError(f"Unknown provider: {self.provider}")

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Generate completion from the LLM

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt

        Returns:
            Generated text response
        """
        try:
            if self.provider == "openai":
                return self._generate_openai(prompt, system_prompt)
            elif self.provider == "anthropic":
                return self._generate_anthropic(prompt, system_prompt)
            elif self.provider == "gemini":
                return self._generate_gemini(prompt, system_prompt)
            elif self.provider == "local":
                return self._generate_local(prompt, system_prompt)
            else:
                raise ValueError(f"Unknown provider: {self.provider}")

        except Exception as e:
            logger.error(f"Error generating completion: {e}")
            raise

    def _generate_openai(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate completion using OpenAI API"""
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )

        return response.choices[0].message.content

    def _generate_anthropic(
        self, prompt: str, system_prompt: Optional[str] = None
    ) -> str:
        """Generate completion using Anthropic API"""
        kwargs = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "messages": [{"role": "user", "content": prompt}],
        }

        if system_prompt:
            kwargs["system"] = system_prompt

        response = self.client.messages.create(**kwargs)

        return response.content[0].text

    def _generate_gemini(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate completion using Gemini API"""
        # Combine system prompt and user prompt for Gemini
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"

        model = self.client.GenerativeModel(
            model_name=self.model,
            generation_config={
                "temperature": self.temperature,
                "max_output_tokens": self.max_tokens,
            }
        )

        response = model.generate_content(full_prompt)
        return response.text

    def _generate_local(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate completion using local model"""
        raise NotImplementedError("Local model support not yet implemented")

    def parse_json_response(self, response: str) -> Dict[str, Any]:
        """
        Parse JSON response from LLM

        Args:
            response: Raw LLM response

        Returns:
            Parsed JSON dictionary
        """
        try:
            # Try to find JSON block in markdown format
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                json_str = response[start:end].strip()
            elif "```" in response:
                start = response.find("```") + 3
                end = response.find("```", start)
                json_str = response[start:end].strip()
            else:
                json_str = response.strip()

            return json.loads(json_str)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.debug(f"Raw response: {response}")
            # Return a default structure
            return {
                "risk_score": 50,
                "risk_level": "Moderate",
                "key_risk_factors": ["Unable to parse response"],
                "confidence_level": "Low",
                "reasoning": "Failed to parse LLM response",
                "raw_response": response,
            }

    def analyze_credit_risk(self, company_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze credit risk for a company

        Args:
            company_data: Company information dictionary

        Returns:
            Risk analysis results
        """
        from .prompt_templates import PromptTemplates

        prompt = PromptTemplates.credit_risk_analysis_prompt(company_data)
        system_prompt = (
            "You are an expert credit risk analyst with deep knowledge of "
            "financial markets, credit rating methodologies, and risk assessment."
        )

        logger.info(
            f"Analyzing credit risk for {company_data.get('ticker', 'Unknown')}"
        )

        response = self.generate(prompt, system_prompt)
        result = self.parse_json_response(response)

        # Add metadata
        result["ticker"] = company_data.get("ticker")
        result["company_name"] = company_data.get("name")
        result["analysis_timestamp"] = self._get_timestamp()

        return result

    @staticmethod
    def _get_timestamp() -> str:
        """Get current timestamp"""
        from datetime import datetime

        return datetime.now().isoformat()
