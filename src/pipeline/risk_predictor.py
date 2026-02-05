"""Credit Risk Prediction Pipeline"""

import json
from typing import List, Dict, Any
from datetime import datetime
from pathlib import Path
from loguru import logger

from ..data_collector import (
    CompanyInfoCollector,
    FinancialDataCollector,
    MarketDataCollector,
    NewsCollector,
)
from ..features import FinancialFeatureExtractor
from ..llm import LLMInterface


class CreditRiskPredictor:
    """Main pipeline for credit risk prediction"""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the credit risk predictor

        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.llm = self._init_llm()

        logger.info("Credit Risk Predictor initialized")

    def _init_llm(self) -> LLMInterface:
        """Initialize LLM interface from config"""
        llm_config = self.config.get("llm", {})

        return LLMInterface(
            provider=llm_config.get("provider", "openai"),
            model=llm_config.get("model"),
            temperature=llm_config.get("temperature", 0.1),
            max_tokens=llm_config.get("max_tokens", 2000),
        )

    def collect_company_data(self, ticker: str) -> Dict[str, Any]:
        """
        Collect all data for a company

        Args:
            ticker: Company ticker symbol

        Returns:
            Dictionary with all collected data
        """
        logger.info(f"Collecting data for {ticker}")

        # Collect from all sources
        company_info = CompanyInfoCollector.get_company_info(ticker)
        financial_metrics = FinancialDataCollector.get_financial_metrics(ticker)
        market_data = MarketDataCollector.get_market_indicators(ticker)
        news_articles = NewsCollector.get_company_news(ticker, max_articles=20)

        # Additional analysis
        news_sentiment = NewsCollector.analyze_news_sentiment(news_articles)
        news_events = NewsCollector.detect_news_events(news_articles)
        price_anomalies = MarketDataCollector.detect_price_anomalies(ticker)
        z_score = FinancialDataCollector.calculate_z_score(ticker)
        risk_indicators = FinancialFeatureExtractor.compute_risk_indicators(
            financial_metrics
        )

        # Combine all data
        company_data = {
            "ticker": ticker,
            "name": company_info.get("name", ticker),
            "sector": company_info.get("sector", "Unknown"),
            "industry": company_info.get("industry", "Unknown"),
            "country": company_info.get("country", "Unknown"),
            "financial_metrics": financial_metrics,
            "market_data": market_data,
            "recent_news": news_articles,
            "news_sentiment": news_sentiment,
            "news_events": news_events,
            "price_anomalies": price_anomalies,
            "z_score": z_score,
            "risk_indicators": risk_indicators,
            "collection_timestamp": datetime.now().isoformat(),
        }

        return company_data

    def predict_risk(self, ticker: str) -> Dict[str, Any]:
        """
        Predict credit risk for a single company

        Args:
            ticker: Company ticker symbol

        Returns:
            Risk prediction results
        """
        logger.info(f"Predicting risk for {ticker}")

        # Collect data
        company_data = self.collect_company_data(ticker)

        # Analyze with LLM
        risk_analysis = self.llm.analyze_credit_risk(company_data)

        # Add additional context
        risk_analysis["data_quality"] = self._assess_data_quality(company_data)
        risk_analysis["traditional_signals"] = self._get_traditional_signals(
            company_data
        )

        return risk_analysis

    def predict_batch(self, tickers: List[str]) -> List[Dict[str, Any]]:
        """
        Predict risk for multiple companies

        Args:
            tickers: List of company ticker symbols

        Returns:
            List of risk prediction results
        """
        results = []

        logger.info(f"Predicting risk for {len(tickers)} companies")

        for ticker in tickers:
            try:
                result = self.predict_risk(ticker)
                results.append(result)
            except Exception as e:
                logger.error(f"Error predicting risk for {ticker}: {e}")
                results.append(
                    {
                        "ticker": ticker,
                        "error": str(e),
                        "risk_score": None,
                        "risk_level": "ERROR",
                    }
                )

        return results

    def rank_by_risk(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Rank companies by risk score

        Args:
            results: List of risk prediction results

        Returns:
            Sorted list of results (highest risk first)
        """
        # Filter out errors and sort by risk score
        valid_results = [r for r in results if r.get("risk_score") is not None]

        sorted_results = sorted(
            valid_results, key=lambda x: x.get("risk_score", 0), reverse=True
        )

        return sorted_results

    def generate_watchlist(
        self, tickers: List[str], threshold: float = 60
    ) -> Dict[str, Any]:
        """
        Generate a watchlist of high-risk companies

        Args:
            tickers: List of company ticker symbols
            threshold: Risk score threshold for inclusion in watchlist

        Returns:
            Dictionary with watchlist and summary
        """
        logger.info(f"Generating watchlist for {len(tickers)} companies")

        # Predict risk for all companies
        results = self.predict_batch(tickers)

        # Rank by risk
        ranked_results = self.rank_by_risk(results)

        # Filter high risk
        high_risk = [r for r in ranked_results if r.get("risk_score", 0) >= threshold]

        # Generate summary
        watchlist = {
            "generation_timestamp": datetime.now().isoformat(),
            "total_companies_analyzed": len(tickers),
            "high_risk_count": len(high_risk),
            "threshold": threshold,
            "high_risk_companies": high_risk,
            "all_results": ranked_results,
        }

        return watchlist

    def save_results(self, results: Dict[str, Any], filename: str = None):
        """
        Save results to file

        Args:
            results: Results dictionary to save
            filename: Optional filename (auto-generated if not provided)
        """
        output_config = self.config.get("output", {})
        save_path = Path(output_config.get("save_path", "data/results"))
        save_path.mkdir(parents=True, exist_ok=True)

        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"risk_prediction_{timestamp}.json"

        filepath = save_path / filename

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        logger.info(f"Results saved to {filepath}")

        return str(filepath)

    def _assess_data_quality(self, company_data: Dict) -> Dict:
        """Assess quality of collected data"""
        quality = {
            "has_financial_data": bool(company_data.get("financial_metrics")),
            "has_market_data": bool(company_data.get("market_data")),
            "has_news_data": bool(company_data.get("recent_news")),
            "has_z_score": company_data.get("z_score") is not None,
            "data_completeness": 0,
        }

        # Calculate completeness score
        completeness = sum(
            [
                quality["has_financial_data"],
                quality["has_market_data"],
                quality["has_news_data"],
                quality["has_z_score"],
            ]
        )
        quality["data_completeness"] = completeness / 4.0

        return quality

    def _get_traditional_signals(self, company_data: Dict) -> Dict:
        """Get traditional credit risk signals"""
        signals = {}

        # Z-Score signal
        z_score = company_data.get("z_score")
        if z_score is not None:
            if z_score < 1.8:
                signals["z_score_signal"] = "HIGH_RISK"
            elif z_score < 3.0:
                signals["z_score_signal"] = "MODERATE_RISK"
            else:
                signals["z_score_signal"] = "LOW_RISK"

        # Price signal
        market_data = company_data.get("market_data", {})
        price_change_3m = market_data.get("price_change_3m", 0)
        if price_change_3m < -30:
            signals["price_signal"] = "HIGH_RISK"
        elif price_change_3m < -15:
            signals["price_signal"] = "MODERATE_RISK"
        else:
            signals["price_signal"] = "LOW_RISK"

        # News sentiment signal
        news_sentiment = company_data.get("news_sentiment", {})
        sentiment_score = news_sentiment.get("sentiment_score", 0)
        if sentiment_score < -0.3:
            signals["sentiment_signal"] = "NEGATIVE"
        elif sentiment_score > 0.3:
            signals["sentiment_signal"] = "POSITIVE"
        else:
            signals["sentiment_signal"] = "NEUTRAL"

        # Risk indicators
        risk_indicators = company_data.get("risk_indicators", {})
        signals["risk_indicators"] = risk_indicators

        return signals
