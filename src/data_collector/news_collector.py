"""News collector for company news and sentiment"""

import requests
from typing import List, Dict
from datetime import datetime, timedelta
from loguru import logger
from bs4 import BeautifulSoup
import yfinance as yf
from ..utils import cache_manager


class NewsCollector:
    """Collect news articles about companies"""

    @staticmethod
    def get_company_news(ticker: str, max_articles: int = 20) -> List[Dict]:
        """
        Get recent news articles for a company

        Args:
            ticker: Company ticker symbol
            max_articles: Maximum number of articles to return

        Returns:
            List of news article dictionaries
        """
        # Create cache key based on ticker and max_articles
        cache_key = {"ticker": ticker, "max_articles": max_articles, "method": "get_company_news"}
        cached_result = cache_manager.get("news_data", cache_key)
        
        if cached_result is not None:
            logger.info(f"Using cached news for {ticker}")
            return cached_result

        try:
            # Use yfinance to get news (it scrapes from Yahoo Finance)
            stock = yf.Ticker(ticker)
            news = stock.news

            articles = []
            for item in news[:max_articles]:
                article = {
                    "title": item.get("title", ""),
                    "publisher": item.get("publisher", ""),
                    "link": item.get("link", ""),
                    "publish_time": datetime.fromtimestamp(
                        item.get("providerPublishTime", 0)
                    ).strftime("%Y-%m-%d %H:%M:%S"),
                    "type": item.get("type", ""),
                    "thumbnail": item.get("thumbnail", {}).get("resolutions", [{}])[
                        0
                    ].get("url", ""),
                }

                # Try to get summary if available
                if "summary" in item:
                    article["summary"] = item["summary"]

                articles.append(article)

            logger.info(f"Collected {len(articles)} news articles for {ticker}")
            
            # Cache the result
            cache_manager.set("news_data", cache_key, articles)
            
            return articles

        except Exception as e:
            logger.error(f"Error collecting news for {ticker}: {e}")
            
            # Return empty list but cache it to prevent repeated attempts
            empty_result = []
            cache_manager.set("news_data", cache_key, empty_result)
            
            return empty_result

    @staticmethod
    def analyze_news_sentiment(articles: List[Dict]) -> Dict:
        """
        Perform basic sentiment analysis on news headlines

        Args:
            articles: List of news article dictionaries

        Returns:
            Dictionary with sentiment analysis
        """
        if not articles:
            return {
                "sentiment_score": 0,
                "positive_count": 0,
                "negative_count": 0,
                "neutral_count": 0,
            }

        # Simple keyword-based sentiment (can be enhanced with NLP models)
        positive_keywords = [
            "profit",
            "growth",
            "gain",
            "rise",
            "surge",
            "beat",
            "strong",
            "upgrade",
            "bullish",
            "rally",
            "record",
            "high",
            "success",
            "win",
        ]

        negative_keywords = [
            "loss",
            "decline",
            "fall",
            "drop",
            "crash",
            "miss",
            "weak",
            "downgrade",
            "bearish",
            "sell",
            "low",
            "fail",
            "risk",
            "concern",
            "warning",
            "debt",
            "default",
            "bankruptcy",
        ]

        positive_count = 0
        negative_count = 0
        neutral_count = 0

        for article in articles:
            title_lower = article.get("title", "").lower()

            has_positive = any(kw in title_lower for kw in positive_keywords)
            has_negative = any(kw in title_lower for kw in negative_keywords)

            if has_negative:
                negative_count += 1
            elif has_positive:
                positive_count += 1
            else:
                neutral_count += 1

        total = len(articles)
        sentiment_score = (positive_count - negative_count) / total if total > 0 else 0

        return {
            "sentiment_score": sentiment_score,
            "positive_count": positive_count,
            "negative_count": negative_count,
            "neutral_count": neutral_count,
            "total_articles": total,
        }

    @staticmethod
    def detect_news_events(articles: List[Dict]) -> List[str]:
        """
        Detect significant events from news

        Args:
            articles: List of news article dictionaries

        Returns:
            List of detected event types
        """
        events = []

        event_keywords = {
            "earnings": ["earnings", "quarterly", "q1", "q2", "q3", "q4", "report"],
            "acquisition": ["acquire", "merger", "acquisition", "buyout"],
            "legal": ["lawsuit", "court", "legal", "sue", "investigation"],
            "management": ["ceo", "cfo", "executive", "resign", "appoint"],
            "product": ["launch", "product", "release", "announce"],
            "regulatory": ["sec", "regulation", "compliance", "fda"],
            "financial_distress": [
                "debt",
                "default",
                "bankruptcy",
                "restructuring",
                "liquidity",
            ],
        }

        for article in articles:
            title_lower = article.get("title", "").lower()

            for event_type, keywords in event_keywords.items():
                if any(kw in title_lower for kw in keywords):
                    if event_type not in events:
                        events.append(event_type)

        return events
