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

## How It Works

```
1. LLM analyzes current market → Identifies risk areas
2. Automatically selects 10-20 high-risk companies
3. Collects financial data, market data, news
4. LLM performs credit risk analysis
5. Generates risk scores and explanations
6. Saves results to data/results/
```

## Configuration

Edit `config/config.yaml`:

```yaml
# How many companies to analyze
prediction:
  top_k_companies: 10  # Free tier: keep ≤ 5 to avoid quota

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
