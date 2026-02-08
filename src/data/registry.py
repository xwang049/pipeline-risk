"""Data source registry for dynamic source management"""

from typing import Dict, Type, List
from loguru import logger
from .base import DataSource


class DataSourceRegistry:
    """
    Registry pattern for data sources (inspired by HELM's plug-in architecture)

    Allows dynamic registration and creation of data sources without
    modifying core code. New data sources can be added by:
    1. Implementing DataSource interface
    2. Registering with DataSourceRegistry.register()

    Example:
        >>> DataSourceRegistry.register("yahoo", YahooFinanceSource)
        >>> source = DataSourceRegistry.create("yahoo", config)
    """

    _sources: Dict[str, Type[DataSource]] = {}

    @classmethod
    def register(cls, source_type: str, source_class: Type[DataSource]):
        """
        Register a data source class

        Args:
            source_type: Unique identifier (e.g., "yahoo", "local_kb")
            source_class: DataSource subclass

        Raises:
            ValueError: If source_type already registered
        """
        if source_type in cls._sources:
            logger.warning(f"Data source '{source_type}' already registered, overwriting")

        cls._sources[source_type] = source_class
        logger.debug(f"Registered data source: {source_type} -> {source_class.__name__}")

    @classmethod
    def create(cls, source_type: str, config: Dict) -> DataSource:
        """
        Factory method to create data source instance

        Args:
            source_type: Registered source type identifier
            config: Configuration dictionary for the source

        Returns:
            DataSource instance

        Raises:
            ValueError: If source_type not registered
        """
        if source_type not in cls._sources:
            raise ValueError(
                f"Unknown data source type: '{source_type}'. "
                f"Available types: {list(cls._sources.keys())}"
            )

        source_class = cls._sources[source_type]
        try:
            instance = source_class(config)
            logger.info(f"Created data source: {source_type}")
            return instance
        except Exception as e:
            logger.error(f"Failed to create data source '{source_type}': {e}")
            raise

    @classmethod
    def list_sources(cls) -> List[str]:
        """
        List all registered data source types

        Returns:
            List of source type identifiers
        """
        return list(cls._sources.keys())

    @classmethod
    def is_registered(cls, source_type: str) -> bool:
        """
        Check if a source type is registered

        Args:
            source_type: Source type identifier

        Returns:
            True if registered, False otherwise
        """
        return source_type in cls._sources

    @classmethod
    def clear(cls):
        """Clear all registered sources (mainly for testing)"""
        cls._sources.clear()
        logger.debug("Cleared all registered data sources")
