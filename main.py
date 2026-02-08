#!/usr/bin/env python3
"""
Credit Risk Prediction Pipeline - Auto Company Selection
Uses LLM to automatically select high-risk companies based on current market conditions
"""

import yaml
import argparse
from pathlib import Path
from loguru import logger
import sys

# Configure logger
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    level="INFO",
)

from src.pipeline import CreditRiskPredictor, CompanySelector
from src.llm import LLMInterface


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Credit Risk Prediction Pipeline with Time-Travel Backtesting",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Real-time mode (use current date)
  python main.py

  # Backtest mode (simulate past date)
  python main.py --as-of-date 2026-02-01
  python main.py --as-of-date 2026-01-15

  # Specify number of companies
  python main.py --companies 10

  # Combine options
  python main.py --as-of-date 2026-02-01 --companies 10
        """
    )

    parser.add_argument(
        "--as-of-date",
        type=str,
        default=None,
        metavar="YYYY-MM-DD",
        help="Simulate as if today is this date (for backtesting). Example: 2026-02-01"
    )

    parser.add_argument(
        "--companies",
        "-n",
        type=int,
        default=None,
        metavar="N",
        help="Number of companies to analyze (default: from config)"
    )

    parser.add_argument(
        "--config",
        type=str,
        default="config/config.yaml",
        metavar="PATH",
        help="Path to config file (default: config/config.yaml)"
    )

    return parser.parse_args()


def load_config(config_path: str = "config/config.yaml") -> dict:
    """Load configuration from YAML file"""
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config


def main():
    """Main entry point with automatic company selection"""
    # Parse command line arguments
    args = parse_args()

    logger.info("=" * 60)
    logger.info("Credit Risk Prediction Pipeline - Auto Mode")
    logger.info("LLM will select high-risk companies based on current market")
    logger.info("=" * 60)

    # Load configuration
    config = load_config(args.config)

    # Command line arguments override config
    # Get time-travel parameter (CLI > config file)
    as_of_date = args.as_of_date if args.as_of_date else config.get("prediction", {}).get("as_of_date")

    if as_of_date:
        logger.info(f"\n⏰ TIME-TRAVEL MODE: Simulating as of {as_of_date}")
        logger.info(f"   Only using data available before {as_of_date}")
        logger.info(f"   Predicting risk for next 7 days from {as_of_date}")
        if args.as_of_date:
            logger.info(f"   (set via command line)")
        else:
            logger.info(f"   (set via config file)")
    else:
        from datetime import datetime
        as_of_date = datetime.now().strftime("%Y-%m-%d")
        logger.info(f"\n⏰ REAL-TIME MODE: Using current date {as_of_date}")

    # Initialize LLM
    llm_config = config.get("llm", {})
    llm = LLMInterface(
        provider=llm_config.get("provider", "gemini"),
        model=llm_config.get("model"),
        temperature=llm_config.get("temperature", 0.1),
        max_tokens=llm_config.get("max_tokens", 4000),
    )

    # Step 1: Use LLM to select high-risk companies
    logger.info("\n" + "=" * 60)
    logger.info("STEP 1: LLM Selecting High-Risk Companies")
    logger.info("=" * 60)

    selector = CompanySelector(llm)

    # Get number of companies (CLI > config > default)
    num_companies = args.companies if args.companies else config.get("prediction", {}).get("top_k_companies", 10)

    # Get market from config or default to US
    market = config.get("companies", {}).get("market", "US")

    # Select companies using LLM (with time constraint)
    logger.info(f"\nAsking LLM to select {num_companies} high-risk companies...")
    tickers = selector.select_high_risk_companies(num_companies, market, as_of_date=as_of_date)

    if not tickers:
        logger.error("Failed to select companies. Exiting.")
        return

    logger.info(f"\n🎯 LLM Selected {len(tickers)} Companies:")
    logger.info(f"   {', '.join(tickers)}")

    # Step 2: Analyze selected companies
    logger.info("\n" + "=" * 60)
    logger.info("STEP 2: Analyzing Selected Companies with LLM")
    logger.info("=" * 60)

    # Get feature weights
    weights = config.get("prediction", {}).get("weights", {})
    logger.info(f"\n📊 Feature Weights:")
    logger.info(f"   Financial Metrics: {weights.get('financial_metrics', 0.5)*100:.0f}%")
    logger.info(f"   Market Signals: {weights.get('market_signals', 0.35)*100:.0f}%")
    logger.info(f"   News Sentiment: {weights.get('news_sentiment', 0.15)*100:.0f}% (reduced - often noise)")

    # Initialize predictor with time parameter
    predictor = CreditRiskPredictor(config, as_of_date=as_of_date)

    # Generate watchlist
    threshold = config.get("prediction", {}).get("risk_threshold", 0.6) * 100
    watchlist = predictor.generate_watchlist(tickers, threshold=threshold)

    # Display results
    logger.info("\n" + "=" * 60)
    logger.info("RISK ASSESSMENT RESULTS")
    logger.info("=" * 60)

    logger.info(f"Total companies analyzed: {watchlist['total_companies_analyzed']}")
    logger.info(
        f"High-risk companies (score >= {threshold}): {watchlist['high_risk_count']}"
    )
    logger.info("-" * 60)

    # Display high-risk companies
    if watchlist["high_risk_companies"]:
        logger.info("\nHIGH RISK COMPANIES:")
        for i, company in enumerate(watchlist["high_risk_companies"], 1):
            logger.warning(
                f"\n{i}. {company.get('company_name', 'Unknown')} ({company.get('ticker')})"
            )
            logger.warning(f"   Risk Score: {company.get('risk_score', 0)}/100")
            logger.warning(f"   Risk Level: {company.get('risk_level', 'Unknown')}")
            logger.warning(
                f"   Confidence: {company.get('confidence_level', 'Unknown')}"
            )

            # Show key risk factors
            risk_factors = company.get("key_risk_factors", [])
            if risk_factors:
                logger.warning("   Key Risk Factors:")
                for factor in risk_factors[:3]:
                    logger.warning(f"     • {factor}")

            # Show reasoning
            reasoning = company.get("reasoning", "")
            if reasoning:
                logger.warning(f"   Reasoning: {reasoning[:200]}...")

    # Display all companies
    logger.info("\n" + "-" * 60)
    logger.info("ALL COMPANIES (Ranked by Risk):")
    for i, company in enumerate(watchlist["all_results"], 1):
        risk_score = company.get("risk_score", 0)
        ticker = company.get("ticker", "Unknown")
        name = company.get("company_name", ticker)
        level = company.get("risk_level", "Unknown")

        if risk_score >= 60:
            log_func = logger.warning
        else:
            log_func = logger.info

        log_func(f"{i}. {name} ({ticker}): {risk_score}/100 [{level}]")

    # Step 3: Save results
    logger.info("\n" + "=" * 60)
    logger.info("STEP 3: Saving Results")
    logger.info("=" * 60)

    # Add selection info to watchlist
    watchlist["llm_selection"] = {
        "selected_tickers": tickers,
        "selection_timestamp": watchlist["generation_timestamp"],
    }

    filepath = predictor.save_results(watchlist)
    logger.info(f"Detailed results saved to: {filepath}")

    logger.info("\n" + "=" * 60)
    logger.info("Analysis complete!")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
