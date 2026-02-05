#!/usr/bin/env python3
"""
Example usage of Credit Risk Prediction Pipeline
"""

import yaml
from pathlib import Path
from loguru import logger
import sys

# Configure logger
logger.remove()
logger.add(sys.stderr, level="INFO")

from src.pipeline import CreditRiskPredictor


def example_single_company():
    """Example: Analyze a single company"""
    print("\n" + "=" * 60)
    print("Example 1: Analyze Single Company")
    print("=" * 60)

    # Load config
    with open("config/config.yaml") as f:
        config = yaml.safe_load(f)

    # Initialize predictor
    predictor = CreditRiskPredictor(config)

    # Analyze Tesla
    ticker = "TSLA"
    print(f"\nAnalyzing {ticker}...")

    result = predictor.predict_risk(ticker)

    print(f"\n{ticker} Risk Assessment:")
    print(f"  Risk Score: {result.get('risk_score', 'N/A')}/100")
    print(f"  Risk Level: {result.get('risk_level', 'N/A')}")
    print(f"  Confidence: {result.get('confidence_level', 'N/A')}")

    print("\n  Key Risk Factors:")
    for factor in result.get("key_risk_factors", [])[:3]:
        print(f"    • {factor}")

    print(f"\n  Reasoning: {result.get('reasoning', 'N/A')[:200]}...")


def example_batch_analysis():
    """Example: Analyze multiple companies"""
    print("\n" + "=" * 60)
    print("Example 2: Batch Analysis")
    print("=" * 60)

    # Load config
    with open("config/config.yaml") as f:
        config = yaml.safe_load(f)

    # Initialize predictor
    predictor = CreditRiskPredictor(config)

    # Define companies to analyze
    tickers = ["TSLA", "NIO", "BABA"]
    print(f"\nAnalyzing {len(tickers)} companies: {', '.join(tickers)}")

    # Batch prediction
    results = predictor.predict_batch(tickers)

    # Display results
    print("\nResults:")
    for result in results:
        ticker = result.get("ticker", "Unknown")
        risk_score = result.get("risk_score", "N/A")
        risk_level = result.get("risk_level", "N/A")
        print(f"  {ticker}: {risk_score}/100 [{risk_level}]")


def example_watchlist():
    """Example: Generate high-risk watchlist"""
    print("\n" + "=" * 60)
    print("Example 3: Generate Watchlist")
    print("=" * 60)

    # Load config
    with open("config/config.yaml") as f:
        config = yaml.safe_load(f)

    # Initialize predictor
    predictor = CreditRiskPredictor(config)

    # Define companies
    tickers = ["TSLA", "BABA", "NIO", "AMC", "GME"]

    # Set threshold for high risk
    threshold = 60

    print(f"\nGenerating watchlist for {len(tickers)} companies")
    print(f"High-risk threshold: {threshold}")

    # Generate watchlist
    watchlist = predictor.generate_watchlist(tickers, threshold=threshold)

    # Display summary
    print(f"\nTotal companies analyzed: {watchlist['total_companies_analyzed']}")
    print(f"High-risk companies: {watchlist['high_risk_count']}")

    # Display high-risk companies
    if watchlist["high_risk_companies"]:
        print("\nHigh-Risk Companies:")
        for i, company in enumerate(watchlist["high_risk_companies"], 1):
            ticker = company.get("ticker", "Unknown")
            name = company.get("company_name", ticker)
            score = company.get("risk_score", "N/A")
            level = company.get("risk_level", "N/A")

            print(f"\n{i}. {name} ({ticker})")
            print(f"   Risk Score: {score}/100 [{level}]")

            # Show top risk factors
            factors = company.get("key_risk_factors", [])
            if factors:
                print("   Top Risk Factors:")
                for factor in factors[:2]:
                    print(f"     • {factor}")

    # Save results
    filepath = predictor.save_results(watchlist)
    print(f"\nDetailed results saved to: {filepath}")


def example_custom_companies():
    """Example: Analyze custom list of companies"""
    print("\n" + "=" * 60)
    print("Example 4: Custom Company List")
    print("=" * 60)

    # Load config
    with open("config/config.yaml") as f:
        config = yaml.safe_load(f)

    # Initialize predictor
    predictor = CreditRiskPredictor(config)

    # Custom list - mix of US and Chinese companies
    custom_tickers = [
        "TSLA",  # US - Tesla
        "BABA",  # China - Alibaba
        "PDD",   # China - Pinduoduo
        "RIVN",  # US - Rivian
        "LCID",  # US - Lucid Motors
    ]

    print(f"\nAnalyzing custom list: {', '.join(custom_tickers)}")

    # Analyze and rank
    results = predictor.predict_batch(custom_tickers)
    ranked = predictor.rank_by_risk(results)

    print("\nRanked by Risk (Highest to Lowest):")
    for i, result in enumerate(ranked, 1):
        ticker = result.get("ticker", "Unknown")
        name = result.get("company_name", ticker)
        score = result.get("risk_score", "N/A")
        level = result.get("risk_level", "N/A")

        print(f"{i}. {name} ({ticker}): {score}/100 [{level}]")


def main():
    """Run all examples"""
    print("\n" + "=" * 60)
    print("Credit Risk Prediction Pipeline - Examples")
    print("=" * 60)

    try:
        # Check if .env file exists
        if not Path(".env").exists():
            print("\n⚠️  Warning: .env file not found!")
            print("Please create a .env file with your API keys.")
            print("See .env.example for template.\n")
            return

        # Run examples
        print("\nSelect an example to run:")
        print("1. Analyze single company")
        print("2. Batch analysis")
        print("3. Generate watchlist")
        print("4. Custom company list")
        print("5. Run all examples")

        choice = input("\nEnter choice (1-5): ").strip()

        if choice == "1":
            example_single_company()
        elif choice == "2":
            example_batch_analysis()
        elif choice == "3":
            example_watchlist()
        elif choice == "4":
            example_custom_companies()
        elif choice == "5":
            example_single_company()
            example_batch_analysis()
            example_watchlist()
            example_custom_companies()
        else:
            print("Invalid choice. Please run again.")

        print("\n" + "=" * 60)
        print("Examples completed!")
        print("=" * 60 + "\n")

    except Exception as e:
        logger.error(f"Error running examples: {e}")
        raise


if __name__ == "__main__":
    main()
