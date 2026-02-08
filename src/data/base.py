"""Data source base classes and interfaces"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, field


@dataclass
class DataInstance:
    """
    Immutable data instance (inspired by HELM's Instance)

    Represents a single piece of data retrieved from a source.
    Immutable for reproducibility.
    """
    id: str
    data: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = ""

    def __post_init__(self):
        """Ensure immutability by freezing after init"""
        object.__setattr__(self, 'metadata', dict(self.metadata))
        object.__setattr__(self, 'data', dict(self.data))


class DataSource(ABC):
    """
    Abstract base class for all data sources

    Design philosophy (from HELM):
    - Clean separation between data and logic
    - Support time-travel (as_of_date) for backtesting
    - Cacheable for efficiency
    - Validate availability before use

    Examples:
        - YahooFinanceSource: Financial metrics
        - NewsAPISource: News articles
        - LocalKnowledgeBase: Historical data
        - LabDatabaseSource: Lab database (future)
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize data source with configuration

        Args:
            config: Configuration dictionary containing:
                - Any source-specific settings
                - cache_ttl: Cache time-to-live in seconds
                - enabled: Whether source is enabled
        """
        self.config = config
        self.cache = None  # Will be injected by framework
        self._enabled = config.get('enabled', True)

    @abstractmethod
    def fetch(
        self,
        query: Dict[str, Any],
        as_of_date: Optional[datetime] = None
    ) -> List[DataInstance]:
        """
        Fetch data with optional time-travel support

        Args:
            query: Query parameters (source-specific)
                Common keys: ticker, company_name, date_range
            as_of_date: Simulate as if fetching on this date
                Used for backtesting - only return data available before this date

        Returns:
            List of DataInstance objects

        Raises:
            ValueError: If query is invalid
            ConnectionError: If source is unavailable
        """
        pass

    @abstractmethod
    def validate(self) -> bool:
        """
        Validate that data source is available and configured correctly

        Returns:
            True if source is ready to use, False otherwise

        Example:
            - Check API keys are set
            - Test connection to database
            - Verify file paths exist
        """
        pass

    @property
    @abstractmethod
    def source_type(self) -> str:
        """
        Return unique source type identifier

        Format: "category:provider"
        Examples:
            - "financial:yahoo"
            - "news:newsapi"
            - "knowledge_base:local"
            - "lab:database"
        """
        pass

    @property
    def is_enabled(self) -> bool:
        """Check if data source is enabled"""
        return self._enabled

    def set_cache(self, cache):
        """Inject cache manager (Dependency Injection pattern)"""
        self.cache = cache

    def _get_from_cache(self, cache_key: str) -> Optional[List[DataInstance]]:
        """Helper to get data from cache"""
        if self.cache is None:
            return None
        return self.cache.get(self.source_type, cache_key)

    def _set_to_cache(self, cache_key: str, data: List[DataInstance]):
        """Helper to set data to cache"""
        if self.cache is not None:
            ttl = self.config.get('cache_ttl', 3600)
            self.cache.set(self.source_type, cache_key, data, ttl=ttl)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(type={self.source_type}, enabled={self.is_enabled})"
