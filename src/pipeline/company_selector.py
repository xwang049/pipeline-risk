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
        self, num_companies: int = 10, market: str = "US", as_of_date: str = None
    ) -> List[str]:
        """
        Use LLM to select high-risk companies based on market conditions

        IMPORTANT: Only selects companies that are:
        1. Currently trading (not delisted/bankrupt)
        2. Have recent data available
        3. Are at risk of FUTURE problems (not already failed)

        Args:
            num_companies: Number of companies to select
            market: Market to focus on (US, China, Global)
            as_of_date: Simulate as if today is this date (YYYY-MM-DD)
                       If None, uses current date

        Returns:
            List of company ticker symbols (verified as tradeable)
        """
        if as_of_date:
            logger.info(
                f"Using LLM to select {num_companies} high-risk companies from {market} market (as of {as_of_date})"
            )
        else:
            logger.info(
                f"Using LLM to select {num_companies} high-risk companies from {market} market"
            )

        # Request more companies than needed since we'll filter out invalid ones
        request_count = num_companies * 3

        prompt = self._create_selection_prompt(request_count, market, as_of_date)
        system_prompt = "You are an expert financial analyst specializing in credit risk and distressed companies."

        response = self.llm.generate(prompt, system_prompt)
        companies = self._parse_company_list(response)

        logger.info(f"LLM suggested {len(companies)} companies, validating...")

        # Validate companies are currently trading
        valid_companies = self._validate_companies(companies)

        logger.info(f"After validation: {len(valid_companies)} valid companies")

        if len(valid_companies) < num_companies:
            logger.warning(
                f"Only found {len(valid_companies)} valid companies, requested {num_companies}"
            )

        return valid_companies[:num_companies]

    def _create_selection_prompt(self, num_companies: int, market: str, as_of_date: str = None) -> str:
        """Create prompt for LLM to select companies"""
        if as_of_date:
            current_date = as_of_date
            time_constraint = f"""
🚨 CRITICAL TIME CONSTRAINT 🚨:
You are simulating as if today is {as_of_date}.
- You may ONLY use information available BEFORE {as_of_date}
- You CANNOT use any information from AFTER {as_of_date}
- This is for backtesting - predict based on {as_of_date} data ONLY
"""
        else:
            current_date = datetime.now().strftime("%Y-%m-%d")
            time_constraint = ""

        prompt = f"""Today is {current_date}.
{time_constraint}

As a credit risk analyst, identify {num_companies} publicly traded companies in the {market} market that are at HIGH RISK of facing financial distress in the NEXT 7 DAYS.

🚨 CRITICAL REQUIREMENTS 🚨:
1. **ONLY companies that are ACTIVELY TRADING RIGHT NOW** (as of {current_date})
   - Do NOT suggest companies that have already filed for bankruptcy
   - Do NOT suggest companies that are already delisted
   - Do NOT suggest companies that failed months/years ago

2. **FORWARD-LOOKING prediction, NOT backward-looking analysis**
   - We want companies that MIGHT fail in the NEXT 7 days
   - NOT companies that already failed in the past
   - Focus on CURRENT vulnerabilities, not historical failures

3. **Companies must have recent public data available**
   - Recently traded (within last few days)
   - Recent news available (within last 1-2 months)
   - Active SEC filings

Selection Criteria:
- **Recent negative developments** (last 1-2 months): earnings misses, executive departures, covenant breaches
- **Current structural problems**: high debt maturing soon, cash burn, losses
- **Industry headwinds NOW**: current sector problems, not historical
- **Recent market signals**: price drops in last month, volatility spikes
- **Upcoming catalysts**: earnings reports next week, debt payments due soon

**EXAMPLES OF WHAT TO AVOID**:
❌ FSR (Fisker) - already bankrupt in 2023
❌ EXPR (Express) - already delisted
❌ Companies that were problems in 2023-2024 but already resolved
❌ Historical bankruptcies

**WHAT TO INCLUDE**:
✅ Companies with earnings reports coming up that might miss
✅ Companies with debt maturing in next few weeks
✅ Companies burning cash NOW and running low
✅ Companies facing NEW regulatory issues
✅ Companies with recent management departures

Market Context ({current_date}):
- Interest rates still elevated
- Look for companies refinancing debt NOW
- Recent sector rotations
- Companies missing Q4 2025 / Q1 2026 targets

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
        Parse company list from LLM response with improved error handling

        Args:
            response: LLM response

        Returns:
            List of ticker symbols
        """
        try:
            # Try to parse JSON response
            data = self.llm.parse_json_response(response)

            # Check if parsing actually failed (returns default structure)
            if data.get("reasoning") == "Failed to parse LLM response":
                logger.warning("JSON parsing returned default structure")
                raise ValueError("JSON parsing failed")

            companies = data.get("companies", [])

            if not companies:
                logger.warning("No companies found in JSON response")
                raise ValueError("Empty companies list")

            tickers = [c.get("ticker") for c in companies if c.get("ticker")]

            if not tickers:
                logger.warning("No valid tickers found in companies list")
                raise ValueError("No tickers extracted")

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
                    logger.info(f"  - {ticker}: {reason[:100]}... [{risk_level}]")

            return tickers

        except Exception as e:
            logger.error(f"Error parsing company list: {e}")

            # Strategy 1: Try enhanced fallback extraction
            logger.warning("Attempting enhanced ticker extraction from response...")
            tickers = self._extract_tickers_enhanced(response)

            if tickers:
                logger.info(f"Enhanced extraction found {len(tickers)} tickers: {', '.join(tickers)}")
                return tickers

            # Strategy 2: Try basic fallback
            logger.warning("Attempting basic fallback ticker extraction...")
            tickers = self._extract_tickers_fallback(response)

            if tickers:
                logger.info(f"Basic fallback found {len(tickers)} tickers: {', '.join(tickers)}")
                return tickers

            # Strategy 3: Use default list
            logger.warning("All extraction methods failed - using default high-risk companies")
            return [
                "BYND",
                "AMC",
                "PLUG",
                "NIO",
                "CVNA",
            ]

    def _extract_tickers_enhanced(self, response: str) -> List[str]:
        """
        Enhanced ticker extraction from partial/malformed JSON

        Looks for ticker values in JSON-like structures even if incomplete

        Args:
            response: LLM response text

        Returns:
            List of ticker symbols
        """
        import re

        tickers = []

        # Pattern 1: "ticker": "XXXX"
        ticker_field_pattern = r'"ticker"\s*:\s*"([A-Z]{1,5})"'
        matches = re.findall(ticker_field_pattern, response)
        tickers.extend(matches)

        # Pattern 2: Ticker at start of line in JSON array
        # Handles truncated responses like:
        #   {
        #     "ticker": "FSR",
        array_ticker_pattern = r'{\s*"ticker"\s*:\s*"([A-Z]{1,5})"'
        matches = re.findall(array_ticker_pattern, response)
        tickers.extend(matches)

        # Remove duplicates while preserving order
        seen = set()
        unique_tickers = []
        for ticker in tickers:
            if ticker not in seen:
                seen.add(ticker)
                unique_tickers.append(ticker)

        return unique_tickers

    def _extract_tickers_fallback(self, response: str) -> List[str]:
        """
        Basic fallback method to extract tickers from response text

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
            'JSON', 'RISK', 'DEBT', 'CASH', 'EV', 'AI', 'IPO',
            'API', 'CEO', 'CFO', 'Q1', 'Q2', 'Q3', 'Q4', 'YOY',
            'KEY', 'NEW', 'OLD', 'HAS', 'NOT', 'ARE', 'CAN', 'MAY'
        }

        tickers = []
        for ticker in potential_tickers:
            if ticker not in exclude_words and len(ticker) <= 5:
                if ticker not in tickers:  # Avoid duplicates
                    tickers.append(ticker)

        return tickers[:20]  # Limit to 20

    def _validate_companies(self, tickers: List[str]) -> List[str]:
        """
        Validate that companies are currently trading and have recent data

        Args:
            tickers: List of ticker symbols to validate

        Returns:
            List of valid tickers
        """
        import yfinance as yf
        from datetime import timedelta

        valid_tickers = []
        today = datetime.now()
        cutoff_date = today - timedelta(days=30)  # Must have traded in last 30 days

        logger.info(f"Validating {len(tickers)} companies...")

        for ticker in tickers:
            try:
                stock = yf.Ticker(ticker)

                # Try to get recent history
                hist = stock.history(period="1mo")

                if hist.empty:
                    logger.warning(f"  X {ticker}: No recent trading data")
                    continue

                # Check last trading date (handle timezone-aware timestamps)
                last_date = hist.index[-1]
                if hasattr(last_date, 'tz_localize'):
                    # Already timezone-aware, convert to naive
                    last_date = last_date.replace(tzinfo=None)
                elif hasattr(last_date, 'to_pydatetime'):
                    last_date = last_date.to_pydatetime()
                    if last_date.tzinfo is not None:
                        last_date = last_date.replace(tzinfo=None)

                if last_date < cutoff_date:
                    logger.warning(
                        f"  X {ticker}: Last traded {last_date.date()} (too old)"
                    )
                    continue

                # Check current price exists
                current_price = hist['Close'].iloc[-1]
                if current_price is None or current_price <= 0:
                    logger.warning(f"  X {ticker}: Invalid price data")
                    continue

                logger.info(f"  OK {ticker}: Valid (last traded {last_date.date()}, price ${current_price:.2f})")
                valid_tickers.append(ticker)

            except Exception as e:
                logger.warning(f"  X {ticker}: Validation failed - {str(e)[:60]}")
                continue

        return valid_tickers

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
