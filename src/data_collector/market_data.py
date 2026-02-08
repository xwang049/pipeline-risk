"""Market data collector"""

import yfinance as yf
import pandas as pd
from typing import Dict
from datetime import datetime, timedelta
from loguru import logger
from ..utils import cache_manager


class MarketDataCollector:
    """Collect market data and price history"""

    @staticmethod
    def get_market_indicators(ticker: str, days: int = 90) -> Dict:
        """
        Get market indicators and price movements

        Args:
            ticker: Company ticker symbol
            days: Number of days of history to analyze

        Returns:
            Dictionary with market indicators
        """
        # Create cache key based on ticker and days
        cache_key = {"ticker": ticker, "days": days, "method": "get_market_indicators"}
        cached_result = cache_manager.get("market_data", cache_key)
        
        if cached_result is not None:
            logger.info(f"Using cached market indicators for {ticker}")
            return cached_result

        try:
            stock = yf.Ticker(ticker)

            # Get historical data
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            hist = stock.history(start=start_date, end=end_date)

            if hist.empty:
                logger.warning(f"No historical data for {ticker}")
                empty_result = {}
                
                # Cache the empty result too to avoid repeated failed attempts
                cache_manager.set("market_data", cache_key, empty_result)
                
                return empty_result

            # Calculate indicators
            current_price = hist["Close"].iloc[-1]
            price_1w_ago = hist["Close"].iloc[-5] if len(hist) >= 5 else current_price
            price_1m_ago = hist["Close"].iloc[-20] if len(hist) >= 20 else current_price
            price_3m_ago = hist["Close"].iloc[0]

            indicators = {
                "current_price": float(current_price),
                "price_change_1w": float(
                    (current_price - price_1w_ago) / price_1w_ago * 100
                ),
                "price_change_1m": float(
                    (current_price - price_1m_ago) / price_1m_ago * 100
                ),
                "price_change_3m": float(
                    (current_price - price_3m_ago) / price_3m_ago * 100
                ),
                "avg_volume": float(hist["Volume"].mean()),
                "volume_change": float(
                    (hist["Volume"].iloc[-1] - hist["Volume"].mean())
                    / hist["Volume"].mean()
                    * 100
                ),
                "volatility": float(hist["Close"].pct_change().std() * 100),
                "52w_high": float(hist["Close"].max()),
                "52w_low": float(hist["Close"].min()),
                "distance_from_high": float(
                    (current_price - hist["Close"].max()) / hist["Close"].max() * 100
                ),
            }

            logger.info(f"Collected market indicators for {ticker}")
            
            # Cache the result
            cache_manager.set("market_data", cache_key, indicators)
            
            return indicators

        except Exception as e:
            logger.error(f"Error collecting market data for {ticker}: {e}")
            
            # Return empty dict but also cache it to prevent repeated attempts in short term
            error_result = {"error": str(e)}
            cache_manager.set("market_data", cache_key, error_result)
            
            return error_result

    @staticmethod
    def get_recent_price_action(ticker: str, days: int = 30) -> pd.DataFrame:
        """
        Get recent price action data

        Args:
            ticker: Company ticker symbol
            days: Number of days of history

        Returns:
            DataFrame with price history
        """
        try:
            stock = yf.Ticker(ticker)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            hist = stock.history(start=start_date, end=end_date)

            return hist

        except Exception as e:
            logger.error(f"Error getting price action for {ticker}: {e}")
            return pd.DataFrame()

    @staticmethod
    def detect_price_anomalies(ticker: str, threshold: float = 2.0) -> Dict:
        """
        Detect unusual price movements

        Args:
            ticker: Company ticker symbol
            threshold: Standard deviation threshold for anomaly detection

        Returns:
            Dictionary with anomaly information
        """
        try:
            hist = MarketDataCollector.get_recent_price_action(ticker, days=90)

            if hist.empty:
                return {}

            # Calculate daily returns
            returns = hist["Close"].pct_change()

            # Detect anomalies (returns beyond threshold * std dev)
            mean_return = returns.mean()
            std_return = returns.std()

            anomalies = returns[
                (returns > mean_return + threshold * std_return)
                | (returns < mean_return - threshold * std_return)
            ]

            anomaly_info = {
                "has_anomalies": len(anomalies) > 0,
                "anomaly_count": len(anomalies),
                "max_gain": float(returns.max() * 100) if not returns.empty else 0,
                "max_loss": float(returns.min() * 100) if not returns.empty else 0,
                "recent_anomalies": [
                    {
                        "date": date.strftime("%Y-%m-%d"),
                        "return": float(ret * 100),
                    }
                    for date, ret in anomalies.tail(5).items()
                ],
            }

            return anomaly_info

        except Exception as e:
            logger.error(f"Error detecting anomalies for {ticker}: {e}")
            return {}
