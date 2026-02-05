"""Financial data collector"""

import yfinance as yf
from typing import Dict, Optional
from loguru import logger


class FinancialDataCollector:
    """Collect financial metrics and ratios"""

    @staticmethod
    def get_financial_metrics(ticker: str) -> Dict:
        """
        Get key financial metrics for a company

        Args:
            ticker: Company ticker symbol

        Returns:
            Dictionary with financial metrics
        """
        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            metrics = {
                # Profitability
                "gross_margin": info.get("grossMargins"),
                "operating_margin": info.get("operatingMargins"),
                "profit_margin": info.get("profitMargins"),
                "roe": info.get("returnOnEquity"),
                "roa": info.get("returnOnAssets"),
                # Liquidity
                "current_ratio": info.get("currentRatio"),
                "quick_ratio": info.get("quickRatio"),
                # Leverage
                "debt_to_equity": info.get("debtToEquity"),
                "total_debt": info.get("totalDebt"),
                "total_cash": info.get("totalCash"),
                # Cash Flow
                "free_cash_flow": info.get("freeCashflow"),
                "operating_cash_flow": info.get("operatingCashflow"),
                # Valuation
                "pe_ratio": info.get("trailingPE"),
                "forward_pe": info.get("forwardPE"),
                "pb_ratio": info.get("priceToBook"),
                # Growth
                "revenue_growth": info.get("revenueGrowth"),
                "earnings_growth": info.get("earningsGrowth"),
            }

            # Calculate additional ratios
            if metrics["total_debt"] and metrics["total_cash"]:
                metrics["net_debt"] = metrics["total_debt"] - metrics["total_cash"]

            # Clean up None values for display
            metrics = {k: v for k, v in metrics.items() if v is not None}

            logger.info(f"Collected {len(metrics)} financial metrics for {ticker}")
            return metrics

        except Exception as e:
            logger.error(f"Error collecting financial data for {ticker}: {e}")
            return {"error": str(e)}

    @staticmethod
    def get_balance_sheet_summary(ticker: str) -> Dict:
        """
        Get balance sheet summary

        Args:
            ticker: Company ticker symbol

        Returns:
            Dictionary with balance sheet data
        """
        try:
            stock = yf.Ticker(ticker)
            balance_sheet = stock.balance_sheet

            if balance_sheet.empty:
                return {}

            # Get most recent quarter
            latest = balance_sheet.iloc[:, 0]

            summary = {
                "total_assets": latest.get("Total Assets"),
                "total_liabilities": latest.get("Total Liabilities Net Minority Interest"),
                "stockholders_equity": latest.get("Stockholders Equity"),
                "cash_and_equivalents": latest.get("Cash And Cash Equivalents"),
                "total_debt": latest.get("Total Debt"),
            }

            return {k: float(v) if v is not None else None for k, v in summary.items()}

        except Exception as e:
            logger.error(f"Error getting balance sheet for {ticker}: {e}")
            return {}

    @staticmethod
    def calculate_z_score(ticker: str) -> Optional[float]:
        """
        Calculate Altman Z-Score for bankruptcy prediction

        Z = 1.2*X1 + 1.4*X2 + 3.3*X3 + 0.6*X4 + 1.0*X5

        Where:
        X1 = Working Capital / Total Assets
        X2 = Retained Earnings / Total Assets
        X3 = EBIT / Total Assets
        X4 = Market Value of Equity / Total Liabilities
        X5 = Sales / Total Assets

        Args:
            ticker: Company ticker symbol

        Returns:
            Z-Score or None if calculation fails
        """
        try:
            stock = yf.Ticker(ticker)
            balance_sheet = stock.balance_sheet
            income_stmt = stock.income_stmt
            info = stock.info

            if balance_sheet.empty or income_stmt.empty:
                return None

            # Get most recent data
            bs = balance_sheet.iloc[:, 0]
            inc = income_stmt.iloc[:, 0]

            # Calculate components
            total_assets = bs.get("Total Assets")
            current_assets = bs.get("Current Assets")
            current_liabilities = bs.get("Current Liabilities")
            retained_earnings = bs.get("Retained Earnings")
            ebit = inc.get("EBIT")
            total_liabilities = bs.get("Total Liabilities Net Minority Interest")
            revenue = inc.get("Total Revenue")
            market_cap = info.get("marketCap")

            if None in [
                total_assets,
                current_assets,
                current_liabilities,
                total_liabilities,
            ]:
                return None

            working_capital = current_assets - current_liabilities
            x1 = working_capital / total_assets
            x2 = (
                retained_earnings / total_assets if retained_earnings is not None else 0
            )
            x3 = ebit / total_assets if ebit is not None else 0
            x4 = market_cap / total_liabilities if market_cap is not None else 0
            x5 = revenue / total_assets if revenue is not None else 0

            z_score = 1.2 * x1 + 1.4 * x2 + 3.3 * x3 + 0.6 * x4 + 1.0 * x5

            logger.info(f"Calculated Z-Score for {ticker}: {z_score:.2f}")
            return float(z_score)

        except Exception as e:
            logger.error(f"Error calculating Z-Score for {ticker}: {e}")
            return None
