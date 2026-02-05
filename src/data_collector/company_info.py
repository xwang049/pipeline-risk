"""Company information collector"""

import yfinance as yf
from typing import Dict, Optional
from loguru import logger


class CompanyInfoCollector:
    """Collect basic company information"""

    @staticmethod
    def get_company_info(ticker: str) -> Dict:
        """
        Get company basic information

        Args:
            ticker: Company ticker symbol

        Returns:
            Dictionary with company information
        """
        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            company_info = {
                "ticker": ticker,
                "name": info.get("longName", ticker),
                "sector": info.get("sector", "Unknown"),
                "industry": info.get("industry", "Unknown"),
                "country": info.get("country", "Unknown"),
                "market_cap": info.get("marketCap"),
                "employees": info.get("fullTimeEmployees"),
                "description": info.get("longBusinessSummary", ""),
                "website": info.get("website", ""),
            }

            logger.info(f"Collected info for {ticker}: {company_info['name']}")
            return company_info

        except Exception as e:
            logger.error(f"Error collecting info for {ticker}: {e}")
            return {
                "ticker": ticker,
                "name": ticker,
                "sector": "Unknown",
                "industry": "Unknown",
                "country": "Unknown",
                "error": str(e),
            }
