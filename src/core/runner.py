"""Benchmark runner - main orchestrator"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path
import json
from loguru import logger

from ..scenarios.credit_risk import CreditRiskScenario
from ..adapters import LLMAdapter
from ..llm import LLMInterface


@dataclass
class RunSpec:
    """
    Specification for a benchmark run

    Defines what to evaluate (scenario) with which model (adapter).
    """
    scenario: CreditRiskScenario
    adapter: LLMAdapter
    config: Dict[str, Any]
    run_name: Optional[str] = None


class BenchmarkRunner:
    """
    Main benchmark orchestrator (inspired by HELM's Runner)

    Responsibilities:
    1. Execute run specifications
    2. Collect predictions from LLM
    3. Track metrics (cost, latency)
    4. Save results

    Usage:
        runner = BenchmarkRunner([run_spec1, run_spec2])
        results = runner.run()
    """

    def __init__(self, run_specs: List[RunSpec], output_dir: str = "experiments/runs"):
        """
        Initialize runner

        Args:
            run_specs: List of run specifications to execute
            output_dir: Directory to save results
        """
        self.run_specs = run_specs
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Initialized BenchmarkRunner with {len(run_specs)} run specs")

    def run(self) -> List[Dict[str, Any]]:
        """
        Execute all run specifications

        Returns:
            List of result dictionaries (one per run spec)
        """
        all_results = []

        for i, spec in enumerate(self.run_specs, 1):
            logger.info(f"=" * 60)
            logger.info(f"Run {i}/{len(self.run_specs)}: {spec.run_name or spec.adapter.provider_name}")
            logger.info(f"=" * 60)

            try:
                result = self._execute_run_spec(spec)
                all_results.append(result)

                # Save individual run result
                self._save_result(result, spec)

                # Print summary
                self._print_summary(result, spec)

            except Exception as e:
                logger.error(f"Run failed: {e}")
                all_results.append({
                    'scenario': spec.scenario.scenario_name,
                    'adapter': spec.adapter.provider_name,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                })

        logger.info(f"\nCompleted {len(all_results)} runs")
        return all_results

    def _execute_run_spec(self, spec: RunSpec) -> Dict[str, Any]:
        """Execute a single run specification"""
        start_time = datetime.now()

        # Get instances from scenario
        logger.info("Step 1: Generating evaluation instances")
        instances = spec.scenario.get_instances()
        logger.info(f"Generated {len(instances)} instances")

        # Predict for each instance
        logger.info("Step 2: Running predictions")
        predictions = []

        for instance in instances:
            try:
                prediction = self._predict_instance(instance, spec)
                predictions.append(prediction)

                logger.info(
                    f"  {instance.ticker}: "
                    f"Risk={prediction.get('risk_score', 'N/A')}/100 "
                    f"({prediction.get('risk_level', 'Unknown')})"
                )

            except Exception as e:
                logger.error(f"Prediction failed for {instance.ticker}: {e}")
                predictions.append({
                    'ticker': instance.ticker,
                    'error': str(e),
                    'risk_score': None,
                    'risk_level': 'ERROR'
                })

        # Compile results
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        result = {
            'scenario': spec.scenario.scenario_name,
            'adapter': {
                'provider': spec.adapter.provider_name,
                'model': spec.adapter.model,
                'statistics': spec.adapter.get_statistics()
            },
            'predictions': predictions,
            'config': spec.config,
            'execution': {
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'duration_seconds': duration,
                'instances_count': len(instances),
                'successful_predictions': len([p for p in predictions if not p.get('error')]),
            }
        }

        return result

    def _predict_instance(self, instance, spec: RunSpec) -> Dict[str, Any]:
        """
        Predict risk for a single instance

        Uses the existing LLMInterface analyze_credit_risk method
        """
        # Create LLM interface from adapter config
        llm = LLMInterface(
            provider=spec.adapter.provider_name,
            model=spec.adapter.model,
            temperature=spec.adapter.default_temperature,
            max_tokens=spec.adapter.default_max_tokens,
        )

        # Analyze risk
        result = llm.analyze_credit_risk(
            company_data=instance.company_data,
            as_of_date=spec.scenario.as_of_date,
            weights=spec.scenario.weights
        )

        return result

    def _save_result(self, result: Dict[str, Any], spec: RunSpec):
        """Save result to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{spec.scenario.scenario_name}_{spec.adapter.provider_name}_{timestamp}.json"
        filepath = self.output_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        logger.info(f"Results saved to: {filepath}")

    def _print_summary(self, result: Dict[str, Any], spec: RunSpec):
        """Print execution summary"""
        exec_info = result['execution']
        adapter_stats = result['adapter']['statistics']
        predictions = result['predictions']

        # Count high-risk companies
        high_risk = [
            p for p in predictions
            if p.get('risk_score') and p['risk_score'] >= 60
        ]

        logger.info("\n" + "=" * 60)
        logger.info("EXECUTION SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Duration: {exec_info['duration_seconds']:.1f}s")
        logger.info(f"Companies analyzed: {exec_info['instances_count']}")
        logger.info(f"Successful predictions: {exec_info['successful_predictions']}")
        logger.info(f"High-risk companies (≥60): {len(high_risk)}")
        logger.info(f"\nLLM Statistics:")
        logger.info(f"  Total requests: {adapter_stats['total_requests']}")
        logger.info(f"  Tokens used: {adapter_stats['total_tokens_used']:,}")
        logger.info(f"  Total cost: ${adapter_stats['total_cost_usd']:.4f}")
        logger.info(f"  Success rate: {adapter_stats['success_rate']*100:.1f}%")
        logger.info("=" * 60 + "\n")
