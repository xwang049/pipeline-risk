"""Intelligent company selector using LLM"""

import json
from datetime import datetime
from typing import List, Dict
from loguru import logger

from ..llm import LLMInterface


class CompanySelector:
    """Use LLM to select high-risk companies based on current market conditions"""

    def __init__(self, llm: LLMInterface):
        """
        Initialize company selector

        Args:
            llm: LLM interface
        """
        self.llm = llm

    def select_high_risk_companies(
        self, num_companies: int = 10, market: str = "US"
    ) -> List[str]:
        """
        Use LLM to select high-risk companies based on current market conditions

        Args:
            num_companies: Number of companies to select
            market: Market to focus on (US, China, Global)

        Returns:
            List of company ticker symbols
        """
        logger.info(
            f"Using LLM to select {num_companies} high-risk companies from {market} market"
        )

        prompt = self._create_selection_prompt(num_companies, market)
        system_prompt = "You are an expert financial analyst specializing in credit risk and distressed companies."

        response = self.llm.generate(prompt, system_prompt)
        companies = self._parse_company_list(response)

        logger.info(f"LLM selected {len(companies)} companies: {', '.join(companies)}")

        return companies[:num_companies]

    def _create_selection_prompt(self, num_companies: int, market: str) -> str:
        """Create prompt for LLM to select companies"""
        current_date = datetime.now().strftime("%Y-%m-%d")

        prompt = f"""Today is {current_date}.

As a credit risk analyst, identify {num_companies} publicly traded companies in the {market} market that are at HIGH RISK of facing financial distress in the NEXT 7 DAYS.

Focus on companies that:
1. **Recently reported negative news** (bankruptcy rumors, earnings misses, layoffs, executive departures)
2. **Have structural financial problems** (high debt, negative cash flow, unprofitable)
3. **Face industry headwinds** (declining sectors, regulatory issues, competition)
4. **Show market distress signals** (stock price crashes, high volatility, trading near lows)
5. **Have upcoming catalysts** (debt maturities, earnings reports, regulatory decisions)

Consider recent events in 2024-2025:
- Tech layoffs and AI bubble concerns
- High interest rates impacting debt-heavy companies
- Retail bankruptcies and store closures
- EV companies burning cash
- Crypto market volatility
- Regional bank stress
- Commercial real estate problems
- Streaming/media industry consolidation

**IMPORTANT**:
- Only include companies that are CURRENTLY TRADING on major exchanges (NYSE, NASDAQ, etc.)
- Focus on companies with REAL financial distress, not just volatility
- Include ticker symbols that are valid for US markets (or ADRs for foreign companies)
- Mix of different sectors for diversification

Provide your response in the following JSON format:
```json
{{
    "companies": [
        {{
            "ticker": "XXXX",
            "name": "Company Name",
            "reason": "Brief reason for high risk (1-2 sentences)",
            "risk_level": "Very High/High"
        }}
    ],
    "market_context": "Brief summary of current market conditions affecting these companies"
}}
```

Select exactly {num_companies} companies."""

        return prompt

    def _parse_company_list(self, response: str) -> List[str]:
        """
        Parse company list from LLM response

        Args:
            response: LLM response

        Returns:
            List of ticker symbols
        """
        try:
            # Try to parse JSON response
            data = self.llm.parse_json_response(response)

            companies = data.get("companies", [])

            if not companies:
                logger.warning("No companies found in JSON response")
                raise ValueError("Empty companies list")

            tickers = [c.get("ticker") for c in companies if c.get("ticker")]

            # Log market context if available
            market_context = data.get("market_context", "")
            if market_context:
                logger.info(f"Market context: {market_context}")

            # Log company reasons
            for company in companies:
                ticker = company.get("ticker", "")
                reason = company.get("reason", "")
                risk_level = company.get("risk_level", "")
                if ticker and reason:
                    logger.info(f"  - {ticker}: {reason} [{risk_level}]")

            return tickers

        except Exception as e:
            logger.error(f"Error parsing company list: {e}")
            logger.debug(f"Raw response: {response[:500]}...")

            # Try to extract tickers from response using fallback method
            logger.warning("Attempting fallback ticker extraction from response...")
            tickers = self._extract_tickers_fallback(response)

            if tickers:
                logger.info(f"Fallback extraction found {len(tickers)} tickers")
                return tickers

            logger.warning("Using default high-risk companies")
            # Fallback to default list
            return [
                "BYND",
                "AMC",
                "PLUG",
                "NIO",
                "CVNA",
                "HOOD",
                "SOFI",
                "TLRY",
                "W",
                "SMCI",
            ]

    def _extract_tickers_fallback(self, response: str) -> List[str]:
        """
        Fallback method to extract tickers from response text

        Args:
            response: LLM response text

        Returns:
            List of ticker symbols
        """
        import re

        # Look for patterns like "XXXX" or "ticker": "XXXX"
        ticker_pattern = r'\b[A-Z]{1,5}\b'
        potential_tickers = re.findall(ticker_pattern, response)

        # Filter out common words that aren't tickers
        exclude_words = {
            'USD', 'NYSE', 'NASDAQ', 'USA', 'LLC', 'INC', 'CORP',
            'HIGH', 'VERY', 'LOW', 'THE', 'AND', 'FOR', 'FROM',
            'JSON', 'RISK', 'DEBT', 'CASH', 'EV', 'AI', 'IPO'
        }

        tickers = []
        for ticker in potential_tickers:
            if ticker not in exclude_words and len(ticker) <= 5:
                if ticker not in tickers:  # Avoid duplicates
                    tickers.append(ticker)

        return tickers[:20]  # Limit to 20

    def get_companies_with_context(
        self, num_companies: int = 10, market: str = "US"
    ) -> Dict:
        """
        Get companies with detailed context

        Args:
            num_companies: Number of companies to select
            market: Market to focus on

        Returns:
            Dictionary with companies and context
        """
        prompt = self._create_selection_prompt(num_companies, market)
        system_prompt = "You are an expert financial analyst specializing in credit risk and distressed companies."

        response = self.llm.generate(prompt, system_prompt)

        try:
            data = self.llm.parse_json_response(response)
            return data
        except Exception as e:
            logger.error(f"Error parsing detailed company list: {e}")
            return {
                "companies": [],
                "market_context": "Failed to get market context",
            }
