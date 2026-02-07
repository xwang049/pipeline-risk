#!/usr/bin/env python3
"""
Credit Risk Prediction Pipeline - Auto Company Selection
Uses LLM to automatically select high-risk companies based on current market conditions
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

from src.pipeline import CreditRiskPredictor, CompanySelector
from src.llm import LLMInterface


def load_config(config_path: str = "config/config.yaml") -> dict:
    """Load configuration from YAML file"""
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config


def main():
    """Main entry point with automatic company selection"""
    logger.info("=" * 60)
    logger.info("Credit Risk Prediction Pipeline - Auto Mode")
    logger.info("LLM will select high-risk companies based on current market")
    logger.info("=" * 60)

    # Load configuration
    config = load_config()

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

    # Get number of companies from config or default to 10
    num_companies = config.get("prediction", {}).get("top_k_companies", 10)

    # Get market from config or default to US
    market = config.get("companies", {}).get("market", "US")

    # Select companies using LLM
    logger.info(f"\nAsking LLM to select {num_companies} high-risk companies...")
    tickers = selector.select_high_risk_companies(num_companies, market)

    if not tickers:
        logger.error("Failed to select companies. Exiting.")
        return

    logger.info(f"\n🎯 LLM Selected {len(tickers)} Companies:")
    logger.info(f"   {', '.join(tickers)}")

    # Step 2: Analyze selected companies
    logger.info("\n" + "=" * 60)
    logger.info("STEP 2: Analyzing Selected Companies with LLM")
    logger.info("=" * 60)

    # Initialize predictor
    predictor = CreditRiskPredictor(config)

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
