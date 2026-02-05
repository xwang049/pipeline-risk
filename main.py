#!/usr/bin/env python3
"""
Credit Risk Prediction Pipeline - Main Entry Point
"""

import yaml
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

from src.pipeline import CreditRiskPredictor


def load_config(config_path: str = "config/config.yaml") -> dict:
    """Load configuration from YAML file"""
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    return config


def main():
    """Main entry point"""
    logger.info("=" * 60)
    logger.info("Credit Risk Prediction Pipeline")
    logger.info("LLM + Knowledge Graph for Credit Risk Assessment")
    logger.info("=" * 60)

    # Load configuration
    config = load_config()

    # Initialize predictor
    predictor = CreditRiskPredictor(config)

    # Get companies to analyze
    companies = config.get("companies", {})
    tickers = companies.get("test_set", [])

    if not tickers:
        logger.error("No companies specified in configuration")
        return

    logger.info(f"Analyzing {len(tickers)} companies: {', '.join(tickers)}")
    logger.info("-" * 60)

    # Generate watchlist
    threshold = config.get("prediction", {}).get("risk_threshold", 0.6) * 100
    watchlist = predictor.generate_watchlist(tickers, threshold=threshold)

    # Display results
    logger.info("\n" + "=" * 60)
    logger.info("RISK ASSESSMENT RESULTS")
    logger.info("=" * 60)

    logger.info(f"Total companies analyzed: {watchlist['total_companies_analyzed']}")
    logger.info(f"High-risk companies (score >= {threshold}): {watchlist['high_risk_count']}")
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
            logger.warning(f"   Confidence: {company.get('confidence_level', 'Unknown')}")

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
        ticker = company.get("ticker", 'Unknown')
        name = company.get("company_name", ticker)
        level = company.get("risk_level", 'Unknown')

        if risk_score >= 60:
            log_func = logger.warning
        else:
            log_func = logger.info

        log_func(f"{i}. {name} ({ticker}): {risk_score}/100 [{level}]")

    # Save results
    filepath = predictor.save_results(watchlist)
    logger.info(f"\nDetailed results saved to: {filepath}")

    logger.info("\n" + "=" * 60)
    logger.info("Analysis complete!")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
