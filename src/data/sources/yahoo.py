"""Yahoo Finance data source implementation"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from loguru import logger

from ..base import DataSource, DataInstance
from ...data_collector import FinancialDataCollector, MarketDataCollector, CompanyInfoCollector


class YahooFinanceSource(DataSource):
    """
    Yahoo Finance data source

    Provides:
    - Company information (name, sector, industry)
    - Financial metrics (debt, cash, profitability ratios)
    - Market data (price, volume, returns)
    - Calculated indicators (Z-score, price anomalies)

    Wraps existing collectors into unified DataSource interface.
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.metrics = config.get('metrics', [
            'debt_to_equity', 'current_ratio', 'roe', 'cash_ratio'
        ])

    def fetch(
        self,
        query: Dict[str, Any],
        as_of_date: Optional[datetime] = None
    ) -> List[DataInstance]:
        """
        Fetch financial and market data from Yahoo Finance

        Args:
            query: Must contain 'ticker' key
            as_of_date: Not fully supported by yfinance, but included for consistency

        Returns:
            List of DataInstance objects (one per ticker)
        """
        ticker = query.get('ticker')
        if not ticker:
            raise ValueError("Query must contain 'ticker' key")

        # Check cache
        cache_key = self._build_cache_key(ticker, as_of_date)
        if cached := self._get_from_cache(cache_key):
            logger.debug(f"Cache hit for {ticker} (yahoo)")
            return cached

        logger.info(f"Fetching Yahoo Finance data for {ticker}")

        try:
            # Collect data using existing collectors
            company_info = CompanyInfoCollector.get_company_info(ticker)
            financial_metrics = FinancialDataCollector.get_financial_metrics(ticker)
            market_data = MarketDataCollector.get_market_indicators(ticker)
            price_anomalies = MarketDataCollector.detect_price_anomalies(ticker)
            z_score = FinancialDataCollector.calculate_z_score(ticker)

            # Combine into single data instance
            data = {
                'ticker': ticker,
                'company_info': company_info,
                'financial_metrics': financial_metrics,
                'market_data': market_data,
                'price_anomalies': price_anomalies,
                'z_score': z_score,
            }

            instance = DataInstance(
                id=f"{ticker}_yahoo_{datetime.now().strftime('%Y%m%d')}",
                data=data,
                metadata={
                    'ticker': ticker,
                    'as_of_date': as_of_date.isoformat() if as_of_date else None,
                    'data_type': 'financial_market',
                },
                timestamp=datetime.now(),
                source=self.source_type
            )

            result = [instance]

            # Cache the result
            self._set_to_cache(cache_key, result)

            logger.info(f"Successfully fetched Yahoo Finance data for {ticker}")
            return result

        except Exception as e:
            logger.error(f"Error fetching Yahoo Finance data for {ticker}: {e}")
            # Return empty list on error (non-blocking)
            return []

    def validate(self) -> bool:
        """
        Validate Yahoo Finance access

        Returns:
            True if yfinance is available and working
        """
        try:
            import yfinance as yf
            # Try fetching a known ticker as validation
            test_ticker = yf.Ticker("AAPL")
            hist = test_ticker.history(period="1d")
            return not hist.empty
        except Exception as e:
            logger.warning(f"Yahoo Finance validation failed: {e}")
            return False

    @property
    def source_type(self) -> str:
        return "financial:yahoo"

    def _build_cache_key(self, ticker: str, as_of_date: Optional[datetime]) -> str:
        """Build cache key for a query"""
        date_str = as_of_date.strftime('%Y%m%d') if as_of_date else 'current'
        return f"{ticker}_{date_str}"
