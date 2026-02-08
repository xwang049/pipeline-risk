#!/usr/bin/env python3
"""
Credit Risk Prediction Pipeline - Prefect Orchestration
每天早上自动运行，选择高风险公司并分析
"""

import yaml
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from prefect import flow, task, get_run_logger
from prefect.task_runners import ConcurrentTaskRunner

from src.pipeline import CreditRiskPredictor, CompanySelector
from src.llm import LLMInterface


def load_config(config_path: str = "config/config.yaml") -> dict:
    """加载配置文件"""
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@task(
    name="select-high-risk-companies",
    retries=3,
    retry_delay_seconds=60,
    log_prints=True
)
def select_companies_task(
    num_companies: int = 5,
    market: str = "US",
    as_of_date: Optional[str] = None,
    llm_config: dict = None
) -> List[str]:
    """
    任务：使用LLM选择高风险公司

    参数：
        num_companies: 要选择的公司数量
        market: 市场范围
        as_of_date: 时间旅行日期
        llm_config: LLM配置

    返回：
        公司ticker列表
    """
    logger = get_run_logger()

    logger.info(f"Selecting {num_companies} high-risk companies from {market} market")
    if as_of_date:
        logger.info(f"Time-travel mode: as of {as_of_date}")

    # 初始化LLM
    llm = LLMInterface(
        provider=llm_config.get("provider", "gemini"),
        model=llm_config.get("model"),
        temperature=llm_config.get("temperature", 0.1),
        max_tokens=llm_config.get("max_tokens", 4000),
    )

    # 选择公司
    selector = CompanySelector(llm)
    tickers = selector.select_high_risk_companies(
        num_companies=num_companies,
        market=market,
        as_of_date=as_of_date
    )

    if not tickers:
        raise ValueError("Failed to select any companies")

    logger.info(f"Selected {len(tickers)} companies: {', '.join(tickers)}")
    return tickers


@task(
    name="analyze-company-risk",
    retries=3,
    retry_delay_seconds=60,
    log_prints=True
)
def analyze_company_task(
    ticker: str,
    config: dict,
    as_of_date: Optional[str] = None
) -> Dict[str, Any]:
    """
    任务：分析单个公司的信用风险

    此任务会被并发执行（通过.map()）

    参数：
        ticker: 公司代码
        config: 完整配置
        as_of_date: 时间旅行日期

    返回：
        风险分析结果
    """
    logger = get_run_logger()
    logger.info(f"Analyzing {ticker}...")

    # 初始化预测器
    predictor = CreditRiskPredictor(config, as_of_date=as_of_date)

    # 预测风险（内部已有缓存和重试机制）
    result = predictor.predict_risk(ticker)

    risk_score = result.get("risk_score", "N/A")
    risk_level = result.get("risk_level", "Unknown")
    logger.info(f"{ticker}: Score={risk_score}, Level={risk_level}")

    return result


@task(
    name="aggregate-and-save-results",
    log_prints=True
)
def save_results_task(
    results: List[Dict[str, Any]],
    selected_tickers: List[str],
    threshold: float = 60.0,
    as_of_date: Optional[str] = None
) -> str:
    """
    任务：汇总结果并保存

    参数：
        results: 所有公司的分析结果
        selected_tickers: 选中的ticker列表
        threshold: 高风险阈值
        as_of_date: 时间旅行日期

    返回：
        保存的文件路径
    """
    logger = get_run_logger()

    # 过滤有效结果
    valid_results = [r for r in results if r.get("risk_score") is not None]

    # 按风险评分排序
    sorted_results = sorted(
        valid_results,
        key=lambda x: x.get("risk_score", 0),
        reverse=True
    )

    # 筛选高风险公司
    high_risk = [r for r in sorted_results if r.get("risk_score", 0) >= threshold]

    # 构建watchlist
    watchlist = {
        "generation_timestamp": datetime.now().isoformat(),
        "as_of_date": as_of_date,
        "total_companies_analyzed": len(valid_results),
        "high_risk_count": len(high_risk),
        "threshold": threshold,
        "high_risk_companies": high_risk,
        "all_results": sorted_results,
        "llm_selection": {
            "selected_tickers": selected_tickers,
            "selection_timestamp": datetime.now().isoformat()
        }
    }

    # 保存结果
    output_dir = Path("data/results")
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"risk_prediction_{timestamp}.json"
    filepath = output_dir / filename

    import json
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(watchlist, f, indent=2, ensure_ascii=False)

    logger.info(f"Results saved to: {filepath}")
    logger.info(f"Total companies: {len(valid_results)}")
    logger.info(f"High-risk companies: {len(high_risk)}")

    # 输出高风险公司摘要
    if high_risk:
        logger.info("\nHigh-Risk Companies:")
        for i, company in enumerate(high_risk, 1):
            ticker = company.get("ticker", "Unknown")
            score = company.get("risk_score", 0)
            level = company.get("risk_level", "Unknown")
            logger.info(f"  {i}. {ticker}: {score}/100 [{level}]")

    return str(filepath)


@flow(
    name="credit-risk-prediction-pipeline",
    description="Daily credit risk prediction for high-risk companies",
    task_runner=ConcurrentTaskRunner(),  # 启用并发执行
    log_prints=True
)
def credit_risk_pipeline(
    as_of_date: Optional[str] = None,
    num_companies: int = None,
    config_path: str = "config/config.yaml"
) -> str:
    """
    主流程：信用风险预测Pipeline

    工作流：
    1. 使用LLM选择高风险公司
    2. 并发分析所有公司（使用.map()）
    3. 汇总结果并保存

    参数：
        as_of_date: 时间旅行日期（None=实时模式，"YYYY-MM-DD"=回测模式）
        num_companies: 分析公司数量（None=使用配置文件）
        config_path: 配置文件路径

    返回：
        保存的结果文件路径
    """
    logger = get_run_logger()

    logger.info("=" * 60)
    logger.info("Credit Risk Prediction Pipeline - Prefect Orchestration")
    logger.info("=" * 60)

    # 加载配置
    config = load_config(config_path)

    # 确定参数（CLI > config > default）
    if num_companies is None:
        num_companies = config.get("prediction", {}).get("top_k_companies", 5)

    if as_of_date is None:
        as_of_date = config.get("prediction", {}).get("as_of_date")

    market = config.get("companies", {}).get("market", "US")
    threshold = config.get("prediction", {}).get("risk_threshold", 0.6) * 100

    # 显示模式
    if as_of_date:
        logger.info(f"\n⏰ TIME-TRAVEL MODE: Simulating as of {as_of_date}")
        logger.info(f"   Predicting risk for next 7 days from {as_of_date}")
    else:
        as_of_date_display = datetime.now().strftime("%Y-%m-%d")
        logger.info(f"\n⏰ REAL-TIME MODE: Using current date {as_of_date_display}")

    # 显示特征权重
    weights = config.get("prediction", {}).get("weights", {})
    logger.info(f"\n📊 Feature Weights:")
    logger.info(f"   Financial Metrics: {weights.get('financial_metrics', 0.5)*100:.0f}%")
    logger.info(f"   Market Signals: {weights.get('market_signals', 0.35)*100:.0f}%")
    logger.info(f"   News Sentiment: {weights.get('news_sentiment', 0.15)*100:.0f}%")

    # ========== STEP 1: 选择公司 ==========
    logger.info("\n" + "=" * 60)
    logger.info("STEP 1: Selecting High-Risk Companies")
    logger.info("=" * 60)

    tickers = select_companies_task(
        num_companies=num_companies,
        market=market,
        as_of_date=as_of_date,
        llm_config=config.get("llm", {})
    )

    # ========== STEP 2: 并发分析所有公司 ==========
    logger.info("\n" + "=" * 60)
    logger.info(f"STEP 2: Analyzing {len(tickers)} Companies (Concurrent)")
    logger.info("=" * 60)

    # 使用.map()实现并发执行
    # Prefect会自动并发运行这些任务
    results = analyze_company_task.map(
        ticker=tickers,
        config=[config] * len(tickers),
        as_of_date=[as_of_date] * len(tickers)
    )

    # ========== STEP 3: 保存结果 ==========
    logger.info("\n" + "=" * 60)
    logger.info("STEP 3: Aggregating and Saving Results")
    logger.info("=" * 60)

    filepath = save_results_task(
        results=results,
        selected_tickers=tickers,
        threshold=threshold,
        as_of_date=as_of_date
    )

    logger.info("\n" + "=" * 60)
    logger.info("Pipeline Completed Successfully!")
    logger.info("=" * 60)

    return filepath


# ========== 部署和调度 ==========

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "serve":
        # 部署为定时任务
        print("Deploying pipeline with schedule...")
        credit_risk_pipeline.serve(
            name="daily-morning-prediction",
            cron="0 8 * * *",  # 每天早上8点运行
            parameters={
                "as_of_date": None,  # 实时模式
                "num_companies": 5
            },
            tags=["production", "daily", "risk-prediction"]
        )
    else:
        # 本地运行（测试）
        print("Running pipeline locally (test mode)...")
        result = credit_risk_pipeline(
            as_of_date=None,  # 实时模式，或指定日期如 "2026-02-01"
            num_companies=5
        )
        print(f"\nResults saved to: {result}")
