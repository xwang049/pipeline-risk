#!/usr/bin/env python3
"""
Simple test script to verify Claude API connection and run a single prediction
"""

import yaml
import sys
from loguru import logger
from pathlib import Path

# Fix Windows console encoding
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Configure logger
logger.remove()
logger.add(sys.stderr, level="INFO",
           format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.pipeline import CreditRiskPredictor


def test_claude_api():
    """Test Claude API connection with a simple company analysis"""

    print("\n" + "="*60)
    print("Testing Claude API Connection")
    print("="*60 + "\n")

    # Check if .env exists
    env_path = Path(".env")
    if not env_path.exists():
        print("❌ Error: .env file not found!")
        print("\nPlease create .env file with your Anthropic API key:")
        print("ANTHROPIC_API_KEY=your_key_here")
        return False

    # Check if API key is set
    with open(env_path) as f:
        env_content = f.read()
        if "your_anthropic_api_key_here" in env_content:
            print("❌ Error: Please replace 'your_anthropic_api_key_here' with your actual API key in .env file")
            return False

    # Load config
    logger.info("Loading configuration...")
    with open("config/config.yaml") as f:
        config = yaml.safe_load(f)

    # Verify Claude is configured
    llm_config = config.get("llm", {})
    logger.info(f"LLM Provider: {llm_config.get('provider')}")
    logger.info(f"Model: {llm_config.get('model')}")

    if llm_config.get('provider') != 'anthropic':
        print("\n⚠️  Warning: config.yaml is not set to use 'anthropic'")
        print("Updating config to use Claude...")
        llm_config['provider'] = 'anthropic'
        llm_config['model'] = 'claude-3-5-sonnet-20241022'

    # Initialize predictor
    logger.info("Initializing Credit Risk Predictor...")
    try:
        predictor = CreditRiskPredictor(config)
        logger.info("✓ Predictor initialized successfully")
    except Exception as e:
        print(f"\n❌ Error initializing predictor: {e}")
        return False

    # Test with Tesla (a well-known company with good data availability)
    ticker = "TSLA"

    print(f"\n{'='*60}")
    print(f"Analyzing {ticker} with Claude API")
    print(f"{'='*60}\n")

    logger.info(f"Step 1/3: Collecting data for {ticker}...")
    try:
        company_data = predictor.collect_company_data(ticker)
        logger.info(f"✓ Data collected: {company_data.get('name', ticker)}")
        logger.info(f"  - Sector: {company_data.get('sector', 'Unknown')}")
        logger.info(f"  - Financial metrics: {len(company_data.get('financial_metrics', {}))} items")
        logger.info(f"  - Market data: {len(company_data.get('market_data', {}))} items")
        logger.info(f"  - News articles: {len(company_data.get('recent_news', []))} articles")
    except Exception as e:
        print(f"\n❌ Error collecting data: {e}")
        return False

    logger.info(f"\nStep 2/3: Sending data to Claude for risk analysis...")
    logger.info("(This may take 10-30 seconds...)")

    try:
        result = predictor.predict_risk(ticker)
        logger.info("✓ Analysis complete!")
    except Exception as e:
        print(f"\n❌ Error during prediction: {e}")
        print("\nPossible issues:")
        print("1. Check your ANTHROPIC_API_KEY in .env file")
        print("2. Verify you have API credits")
        print("3. Check your internet connection")
        return False

    # Display results
    print(f"\n{'='*60}")
    print(f"Risk Assessment Results for {ticker}")
    print(f"{'='*60}\n")

    print(f"Company: {result.get('company_name', ticker)}")
    print(f"Ticker: {result.get('ticker', ticker)}")
    print(f"\n{'─'*60}")
    print(f"Risk Score: {result.get('risk_score', 'N/A')}/100")
    print(f"Risk Level: {result.get('risk_level', 'N/A')}")
    print(f"Confidence: {result.get('confidence_level', 'N/A')}")
    print(f"{'─'*60}\n")

    # Key risk factors
    risk_factors = result.get('key_risk_factors', [])
    if risk_factors:
        print("Key Risk Factors:")
        for i, factor in enumerate(risk_factors, 1):
            print(f"  {i}. {factor}")
        print()

    # Early warning signals
    warning_signals = result.get('early_warning_signals', [])
    if warning_signals:
        print("Early Warning Signals:")
        for i, signal in enumerate(warning_signals, 1):
            print(f"  {i}. {signal}")
        print()

    # Adverse event probabilities
    probs = result.get('adverse_event_probabilities', {})
    if probs:
        print("Adverse Event Probabilities:")
        for event, prob in probs.items():
            prob_pct = f"{prob*100:.1f}%" if prob is not None else "N/A"
            print(f"  - {event.replace('_', ' ').title()}: {prob_pct}")
        print()

    # Reasoning
    reasoning = result.get('reasoning', '')
    if reasoning:
        print("Analysis Reasoning:")
        print(f"  {reasoning[:300]}...")
        if len(reasoning) > 300:
            print(f"  (Full reasoning in saved results)")
        print()

    # Traditional signals
    trad_signals = result.get('traditional_signals', {})
    if trad_signals:
        print("Traditional Risk Signals:")
        for signal, value in trad_signals.items():
            if signal != 'risk_indicators':
                print(f"  - {signal.replace('_', ' ').title()}: {value}")
        print()

    # Save results
    logger.info(f"\nStep 3/3: Saving results...")
    try:
        from datetime import datetime
        filename = f"test_result_{ticker}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = predictor.save_results(result, filename)
        logger.info(f"✓ Results saved to: {filepath}")
    except Exception as e:
        print(f"⚠️  Warning: Could not save results: {e}")

    print(f"\n{'='*60}")
    print("✅ Claude API Test Successful!")
    print(f"{'='*60}\n")

    print("Next steps:")
    print("1. Try analyzing other companies by editing this script")
    print("2. Run 'python main.py' to analyze multiple companies")
    print("3. Run 'python example.py' for interactive examples")
    print()

    return True


if __name__ == "__main__":
    try:
        success = test_claude_api()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
