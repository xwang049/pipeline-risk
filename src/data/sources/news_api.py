"""News API data source implementation"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from loguru import logger

from ..base import DataSource, DataInstance
from ...data_collector import NewsCollector


class NewsAPISource(DataSource):
    """
    News API data source

    Provides:
    - Recent company news articles
    - News sentiment analysis
    - News event detection (earnings, management changes, etc.)

    Supports time-travel: filters news by as_of_date for backtesting.

    Wraps existing NewsCollector into unified DataSource interface.
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.max_articles = config.get('max_articles', 20)
        self.lookback_days = config.get('lookback_days', 30)

    def fetch(
        self,
        query: Dict[str, Any],
        as_of_date: Optional[datetime] = None
    ) -> List[DataInstance]:
        """
        Fetch news data

        Args:
            query: Must contain 'ticker' or 'company_name' key
            as_of_date: Filter news to only include articles before this date

        Returns:
            List of DataInstance objects (one per ticker)
        """
        ticker = query.get('ticker')
        if not ticker:
            raise ValueError("Query must contain 'ticker' key")

        # Check cache
        cache_key = self._build_cache_key(ticker, as_of_date)
        if cached := self._get_from_cache(cache_key):
            logger.debug(f"Cache hit for {ticker} (news)")
            return cached

        logger.info(f"Fetching news data for {ticker}")

        try:
            # Fetch news using existing collector
            news_articles = NewsCollector.get_company_news(
                ticker,
                max_articles=self.max_articles
            )

            # Filter by as_of_date if specified
            if as_of_date:
                news_articles = self._filter_news_by_date(news_articles, as_of_date)
                logger.debug(
                    f"Filtered news for {ticker}: "
                    f"{len(news_articles)} articles before {as_of_date.date()}"
                )

            # Analyze sentiment and detect events
            news_sentiment = NewsCollector.analyze_news_sentiment(news_articles)
            news_events = NewsCollector.detect_news_events(news_articles)

            # Combine into single data instance
            data = {
                'ticker': ticker,
                'articles': news_articles,
                'sentiment': news_sentiment,
                'events': news_events,
                'article_count': len(news_articles),
            }

            instance = DataInstance(
                id=f"{ticker}_news_{datetime.now().strftime('%Y%m%d')}",
                data=data,
                metadata={
                    'ticker': ticker,
                    'as_of_date': as_of_date.isoformat() if as_of_date else None,
                    'data_type': 'news',
                    'lookback_days': self.lookback_days,
                },
                timestamp=datetime.now(),
                source=self.source_type
            )

            result = [instance]

            # Cache the result
            self._set_to_cache(cache_key, result)

            logger.info(
                f"Successfully fetched news data for {ticker}: "
                f"{len(news_articles)} articles"
            )
            return result

        except Exception as e:
            logger.error(f"Error fetching news data for {ticker}: {e}")
            # Return empty list on error (non-blocking)
            return []

    def validate(self) -> bool:
        """
        Validate news API access

        Returns:
            True if news collector is working
        """
        try:
            # Try fetching news for a known company
            test_articles = NewsCollector.get_company_news("AAPL", max_articles=1)
            return True  # If no exception, assume working
        except Exception as e:
            logger.warning(f"News API validation failed: {e}")
            return False

    @property
    def source_type(self) -> str:
        return "news:api"

    def _build_cache_key(self, ticker: str, as_of_date: Optional[datetime]) -> str:
        """Build cache key for a query"""
        date_str = as_of_date.strftime('%Y%m%d') if as_of_date else 'current'
        return f"{ticker}_{date_str}"

    def _filter_news_by_date(
        self,
        news_articles: List[Dict],
        as_of_date: datetime
    ) -> List[Dict]:
        """
        Filter news articles to only include those published before as_of_date

        Args:
            news_articles: List of news articles
            as_of_date: Cut-off date

        Returns:
            Filtered list of news articles
        """
        filtered = []

        for article in news_articles:
            pub_date_str = article.get('published_date')
            if not pub_date_str:
                continue

            try:
                # Parse various date formats
                for fmt in ['%Y-%m-%d', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S']:
                    try:
                        pub_date = datetime.strptime(pub_date_str[:19], fmt)
                        break
                    except ValueError:
                        continue
                else:
                    # If no format worked, try ISO format
                    pub_date = datetime.fromisoformat(pub_date_str.replace('Z', '+00:00'))
                    pub_date = pub_date.replace(tzinfo=None)  # Make naive

                # Only include articles published before as_of_date
                if pub_date <= as_of_date:
                    filtered.append(article)

            except Exception as e:
                logger.debug(f"Could not parse date {pub_date_str}: {e}")
                continue

        return filtered
