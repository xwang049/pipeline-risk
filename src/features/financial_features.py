"""Financial feature extraction"""

from typing import Dict
from loguru import logger


class FinancialFeatureExtractor:
    """Extract and compute financial features"""

    @staticmethod
    def compute_risk_indicators(financial_data: Dict) -> Dict:
        """
        Compute risk indicators from financial data

        Args:
            financial_data: Dictionary with financial metrics

        Returns:
            Dictionary with computed risk indicators
        """
        indicators = {}

        try:
            # Leverage risk
            debt_to_equity = financial_data.get("debt_to_equity")
            if debt_to_equity is not None:
                if debt_to_equity > 2.0:
                    indicators["leverage_risk"] = "HIGH"
                elif debt_to_equity > 1.0:
                    indicators["leverage_risk"] = "MEDIUM"
                else:
                    indicators["leverage_risk"] = "LOW"

            # Liquidity risk
            current_ratio = financial_data.get("current_ratio")
            if current_ratio is not None:
                if current_ratio < 1.0:
                    indicators["liquidity_risk"] = "HIGH"
                elif current_ratio < 1.5:
                    indicators["liquidity_risk"] = "MEDIUM"
                else:
                    indicators["liquidity_risk"] = "LOW"

            # Profitability risk
            roe = financial_data.get("roe")
            if roe is not None:
                if roe < 0:
                    indicators["profitability_risk"] = "HIGH"
                elif roe < 0.1:
                    indicators["profitability_risk"] = "MEDIUM"
                else:
                    indicators["profitability_risk"] = "LOW"

            # Cash flow risk
            free_cash_flow = financial_data.get("free_cash_flow")
            if free_cash_flow is not None:
                if free_cash_flow < 0:
                    indicators["cash_flow_risk"] = "HIGH"
                else:
                    indicators["cash_flow_risk"] = "LOW"

        except Exception as e:
            logger.error(f"Error computing risk indicators: {e}")

        return indicators

    @staticmethod
    def normalize_metrics(metrics: Dict) -> Dict:
        """
        Normalize financial metrics for comparison

        Args:
            metrics: Dictionary with raw financial metrics

        Returns:
            Dictionary with normalized metrics
        """
        # Simple normalization (can be enhanced with industry benchmarks)
        normalized = {}

        # Define normal ranges for key metrics
        ranges = {
            "current_ratio": (1.5, 3.0),
            "debt_to_equity": (0.0, 1.0),
            "roe": (0.1, 0.2),
            "operating_margin": (0.1, 0.3),
        }

        for metric, (min_val, max_val) in ranges.items():
            if metric in metrics and metrics[metric] is not None:
                value = metrics[metric]
                # Normalize to 0-1 scale
                normalized[f"{metric}_normalized"] = max(
                    0, min(1, (value - min_val) / (max_val - min_val))
                )

        return normalized
