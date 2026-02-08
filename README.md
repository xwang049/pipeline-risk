# Credit Risk Prediction Pipeline

**AI-powered credit risk assessment using LLM + Financial Data**

Automatically identifies high-risk companies based on current market conditions.

## Quick Start

```bash
# 1. Install dependencies
uv venv
source .venv/Scripts/activate  # Windows
uv pip install -e .

# 2. Add API key
cp .env.example .env
# Edit .env and add: GEMINI_API_KEY=your_key

# 3. Run
python main.py
```

**That's it!** The LLM will automatically:
- Analyze current market conditions
- Select high-risk companies
- Perform comprehensive risk analysis
- Generate detailed reports

## Usage Modes

### 1. Manual Execution (Testing & Backtesting)

```bash
# Real-time analysis
python main.py

# Time-travel backtesting (test prediction accuracy)
python main.py --as-of-date 2026-02-01 --companies 5
```

### 2. Automated Daily Runs (Production)

```bash
# Deploy with Prefect - runs daily at 8:00 AM
python prefect_pipeline.py serve
```

See [PREFECT_DEPLOYMENT.md](PREFECT_DEPLOYMENT.md) for detailed deployment guide.

## How It Works

```
1. LLM analyzes current market → Identifies risk areas
2. Automatically selects 5-10 high-risk companies (currently trading)
3. Collects financial data, market data, news
4. LLM performs credit risk analysis
5. Generates risk scores and explanations
6. Saves results to data/results/
```

## Time-Travel Backtesting

Test prediction accuracy by simulating analysis on historical dates:

```bash
# Simulate as if today is Feb 1, 2026
# Only uses data available BEFORE Feb 1
# Predicts risk for NEXT 7 days (Feb 1-8)
python main.py --as-of-date 2026-02-01 --companies 5
```

**Use case**: Validate model by checking if companies flagged as high-risk on Feb 1 actually faced problems in the following week.

**Time constraint**:
- News articles filtered to only include those published before `as_of_date`
- LLM instructed to ignore any information after `as_of_date`
- Validates forward-looking prediction capability

## Configuration

Edit `config/config.yaml`:

```yaml
# How many companies to analyze
prediction:
  top_k_companies: 5  # Free tier: keep ≤ 5 to avoid quota

  # Feature weights (financial data > market > news)
  weights:
    financial_metrics: 0.50  # Most important
    market_signals: 0.35
    news_sentiment: 0.15     # Least - often noise

  # Optional: set for backtesting
  as_of_date: null  # or "2026-02-01"

# Market scope
companies:
  market: "US"  # Options: US, China, Global

# LLM provider (Gemini is free)
llm:
  provider: "gemini"
  model: "models/gemini-2.5-flash"
```

## Output

Results saved in `data/results/risk_prediction_YYYYMMDD_HHMMSS.json`:

```json
{
  "total_companies_analyzed": 10,
  "high_risk_count": 3,
  "high_risk_companies": [
    {
      "ticker": "BYND",
      "risk_score": 90,
      "risk_level": "Very High",
      "key_risk_factors": [
        "Severe cash burn",
        "Consecutive losses",
        "Declining revenue"
      ],
      "reasoning": "Detailed analysis..."
    }
  ]
}
```

## Cost

| Provider | Model | Cost (10 companies) |
|----------|-------|---------------------|
| **Gemini** | 2.5 Flash | **Free** (20/day limit) |
| OpenAI | gpt-4o-mini | ~$0.06 |
| Anthropic | claude-3-5-haiku | ~$0.45 |

**Tip**: Keep `top_k_companies: 5` for free daily runs.

## API Keys

Get free API key:
- **Gemini**: https://aistudio.google.com/app/apikey (recommended)
- OpenAI: https://platform.openai.com/api-keys
- Anthropic: https://console.anthropic.com/settings/keys

## License

MIT
