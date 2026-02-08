"""Credit risk prediction scenario"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from loguru import logger
from dataclasses import dataclass

from ..data.base import DataSource
from ..adapters import LLMAdapter, LLMRequest
from ..pipeline.company_selector import CompanySelector


@dataclass
class ScenarioInstance:
    """Single evaluation instance for a company"""
    id: str
    ticker: str
    company_data: Dict[str, Any]
    ground_truth: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = None


class CreditRiskScenario:
    """
    Credit risk prediction scenario

    Orchestrates:
    1. Company selection (via LLM or manual)
    2. Data collection from multiple sources
    3. Risk prediction via LLM
    4. Result aggregation
    """

    def __init__(self, config: Dict[str, Any], data_sources: List[DataSource], llm: LLMAdapter):
        """
        Initialize scenario

        Args:
            config: Scenario configuration
            data_sources: List of data sources to query
            llm: LLM adapter for analysis
        """
        self.config = config
        self.data_sources = {source.source_type: source for source in data_sources}
        self.llm = llm

        # Extract config
        self.num_companies = config.get('num_companies', 5)
        self.market = config.get('market', 'US')
        self.as_of_date = config.get('as_of_date')
        self.weights = config.get('weights', {
            'financial_metrics': 0.50,
            'market_signals': 0.35,
            'news_sentiment': 0.15
        })

        logger.info(f"Initialized CreditRiskScenario: {self.num_companies} companies, {len(self.data_sources)} sources")

    def get_instances(self) -> List[ScenarioInstance]:
        """
        Get evaluation instances

        Steps:
        1. Select companies (via LLM or manual)
        2. For each company, collect data from all sources
        3. Create ScenarioInstance objects

        Returns:
            List of ScenarioInstance objects
        """
        logger.info(f"Generating {self.num_companies} scenario instances")

        # Step 1: Select companies
        tickers = self._select_companies()

        # Step 2: Create instances
        instances = []
        for ticker in tickers:
            try:
                company_data = self._collect_company_data(ticker)

                instance = ScenarioInstance(
                    id=f"{ticker}_{self.as_of_date or 'current'}",
                    ticker=ticker,
                    company_data=company_data,
                    metadata={'as_of_date': self.as_of_date}
                )

                instances.append(instance)
                logger.debug(f"Created instance for {ticker}")

            except Exception as e:
                logger.error(f"Failed to create instance for {ticker}: {e}")
                continue

        logger.info(f"Generated {len(instances)} instances")
        return instances

    def _select_companies(self) -> List[str]:
        """Select companies for analysis"""
        selection_mode = self.config.get('selection_mode', 'auto')

        if selection_mode == 'manual':
            # Manual list
            tickers = self.config.get('companies', [])
            logger.info(f"Using manual company list: {tickers}")
            return tickers

        else:
            # Auto-select via LLM
            logger.info("Using LLM to select high-risk companies")
            selector = CompanySelector(self.llm)

            # Convert as_of_date string to datetime if needed
            as_of_date_str = self.as_of_date
            if isinstance(self.as_of_date, datetime):
                as_of_date_str = self.as_of_date.strftime('%Y-%m-%d')

            tickers = selector.select_high_risk_companies(
                num_companies=self.num_companies,
                market=self.market,
                as_of_date=as_of_date_str
            )

            logger.info(f"LLM selected {len(tickers)} companies: {', '.join(tickers)}")
            return tickers

    def _collect_company_data(self, ticker: str) -> Dict[str, Any]:
        """
        Collect data for a company from all sources

        Args:
            ticker: Company ticker

        Returns:
            Dictionary with data from all sources
        """
        company_data = {'ticker': ticker}

        # Parse as_of_date if string
        as_of_date = self.as_of_date
        if isinstance(as_of_date, str):
            as_of_date = datetime.fromisoformat(as_of_date)

        # Query each data source
        for source_type, source in self.data_sources.items():
            if not source.is_enabled:
                logger.debug(f"Skipping disabled source: {source_type}")
                continue

            try:
                query = {'ticker': ticker}
                instances = source.fetch(query, as_of_date)

                if instances:
                    company_data[source_type] = instances[0].data
                    logger.debug(f"Collected data from {source_type} for {ticker}")
                else:
                    company_data[source_type] = None
                    logger.debug(f"No data from {source_type} for {ticker}")

            except Exception as e:
                logger.warning(f"Error fetching from {source_type} for {ticker}: {e}")
                company_data[source_type] = None

        return company_data

    @property
    def scenario_name(self) -> str:
        return "credit_risk_prediction"
