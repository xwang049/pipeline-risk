#!/usr/bin/env python3
"""
Benchmark runner script

Professional benchmark framework for credit risk prediction.
Supports multiple data sources and LLM providers.

Usage:
    python scripts/run_benchmark.py
    python scripts/run_benchmark.py --config config/scenarios/credit_risk.yaml
    python scripts/run_benchmark.py --providers openai gemini
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import yaml
import argparse
from datetime import datetime
from loguru import logger

from src.data.registry import DataSourceRegistry
from src.data.sources import YahooFinanceSource, NewsAPISource, LocalKnowledgeBase, LabDatabaseSource
from src.adapters import AdapterFactory
from src.scenarios.credit_risk import CreditRiskScenario
from src.core.runner import BenchmarkRunner, RunSpec
from src.utils import cache_manager


def load_config(config_path: str) -> dict:
    """Load configuration from YAML file"""
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def load_models_config() -> dict:
    """Load models configuration"""
    models_path = project_root / 'config' / 'config.yaml'
    with open(models_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    return config.get('llm', {})


def setup_data_sources(scenario_config: dict) -> list:
    """
    Initialize and register all data sources

    Returns:
        List of enabled DataSource instances
    """
    # Register all source types
    DataSourceRegistry.register('yahoo', YahooFinanceSource)
    DataSourceRegistry.register('news', NewsAPISource)
    DataSourceRegistry.register('local_kb', LocalKnowledgeBase)
    DataSourceRegistry.register('lab_db', LabDatabaseSource)

    sources = []
    for source_config in scenario_config['scenario']['data_sources']:
        if source_config.get('enabled', True):
            try:
                source = DataSourceRegistry.create(
                    source_config['type'],
                    source_config.get('config', {})
                )

                # Inject cache
                source.set_cache(cache_manager)

                # Validate
                if source.validate():
                    sources.append(source)
                    logger.info(f"✓ Enabled data source: {source.source_type}")
                else:
                    logger.warning(f"✗ Validation failed for: {source.source_type}")

            except Exception as e:
                logger.error(f"Failed to initialize {source_config['type']}: {e}")

    return sources


def create_run_specs(
    scenario_config: dict,
    models_config: dict,
    data_sources: list,
    providers: list
) -> list:
    """
    Create run specifications for each provider

    Args:
        scenario_config: Scenario configuration
        models_config: LLM models configuration
        data_sources: List of data sources
        providers: List of provider names to run

    Returns:
        List of RunSpec objects
    """
    run_specs = []

    for provider in providers:
        try:
            # Create adapter
            adapter = AdapterFactory.create(provider, {
                'model': models_config.get('model'),
                'api_key': None,  # Will load from env
                'temperature': models_config.get('temperature', 0.1),
                'max_tokens': models_config.get('max_tokens', 2000),
            })

            # Create scenario (each provider gets its own scenario instance)
            scenario = CreditRiskScenario(
                config=scenario_config['scenario'],
                data_sources=data_sources,
                llm=adapter  # Adapter acts as LLM interface
            )

            # Create run spec
            run_spec = RunSpec(
                scenario=scenario,
                adapter=adapter,
                config=scenario_config['scenario'],
                run_name=f"{provider}_{scenario.scenario_name}"
            )

            run_specs.append(run_spec)
            logger.info(f"✓ Created run spec for {provider}")

        except Exception as e:
            logger.warning(f"✗ Skipping {provider}: {e}")

    return run_specs


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Run credit risk prediction benchmark"
    )
    parser.add_argument(
        '--config',
        default='config/scenarios/credit_risk.yaml',
        help='Path to scenario configuration file'
    )
    parser.add_argument(
        '--providers',
        nargs='+',
        default=['gemini'],
        help='LLM providers to evaluate (e.g., openai gemini)'
    )
    parser.add_argument(
        '--as-of-date',
        type=str,
        help='Time-travel date for backtesting (YYYY-MM-DD)'
    )
    parser.add_argument(
        '--num-companies',
        type=int,
        help='Override number of companies to analyze'
    )

    args = parser.parse_args()

    # Print banner
    logger.info("=" * 70)
    logger.info(" Credit Risk Prediction Benchmark - Professional Architecture")
    logger.info("=" * 70)
    logger.info(f" Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f" Config: {args.config}")
    logger.info(f" Providers: {', '.join(args.providers)}")
    logger.info("=" * 70 + "\n")

    # Load configurations
    logger.info("Loading configurations...")
    scenario_config = load_config(args.config)
    models_config = load_models_config()

    # Override with CLI arguments
    if args.as_of_date:
        scenario_config['scenario']['as_of_date'] = args.as_of_date
        logger.info(f"⏰ Time-travel mode: {args.as_of_date}")

    if args.num_companies:
        scenario_config['scenario']['num_companies'] = args.num_companies

    # Setup data sources
    logger.info("\nInitializing data sources...")
    data_sources = setup_data_sources(scenario_config)
    logger.info(f"Enabled {len(data_sources)} data sources\n")

    # Create run specifications
    logger.info("Creating run specifications...")
    run_specs = create_run_specs(
        scenario_config,
        models_config,
        data_sources,
        args.providers
    )

    if not run_specs:
        logger.error("No valid run specifications created. Exiting.")
        return 1

    logger.info(f"Created {len(run_specs)} run specifications\n")

    # Run benchmark
    logger.info("Starting benchmark execution...\n")
    runner = BenchmarkRunner(run_specs)
    results = runner.run()

    # Final summary
    logger.info("\n" + "=" * 70)
    logger.info(" Benchmark Complete!")
    logger.info("=" * 70)
    logger.info(f" Total runs: {len(results)}")
    logger.info(f" Successful runs: {len([r for r in results if not r.get('error')])}")
    logger.info(f" Results saved to: experiments/runs/")
    logger.info("=" * 70 + "\n")

    return 0


if __name__ == '__main__':
    sys.exit(main())
