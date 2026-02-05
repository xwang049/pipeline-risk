# Quick Start Guide 🚀

Get started with the Credit Risk Prediction Pipeline in 5 minutes!

## Prerequisites

- Python 3.12+
- uv (package manager)
- API key for OpenAI or Anthropic

## Step-by-Step Setup

### 1. Install Dependencies (30 seconds)

```bash
# The virtual environment should already be created
# Activate it and install dependencies
source .venv/Scripts/activate  # Windows
# source .venv/bin/activate    # macOS/Linux

# Install packages (if not already done)
uv pip install -e .
```

### 2. Configure API Keys (1 minute)

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and add your API key
# For OpenAI:
OPENAI_API_KEY=sk-...your-key-here...

# Or for Anthropic Claude:
ANTHROPIC_API_KEY=sk-ant-...your-key-here...
```

### 3. Test Installation (30 seconds)

```bash
python tests/test_installation.py
```

You should see all tests passing!

### 4. Run Your First Analysis (2 minutes)

```bash
# Run the main pipeline with default companies
python main.py
```

This will:
- Analyze 6 companies (TSLA, BABA, NIO, BIDU, AMC, GME)
- Collect financial data, market data, and news
- Generate risk predictions using LLM
- Save detailed results to `data/results/`

### 5. View Results

Check the output in your terminal, which will show:
- Risk scores for each company (0-100)
- Risk levels (Very Low, Low, Moderate, High, Very High)
- Key risk factors
- High-risk watchlist

Detailed JSON results are saved in `data/results/risk_prediction_YYYYMMDD_HHMMSS.json`

## Example Output

```
============================================================
RISK ASSESSMENT RESULTS
============================================================
Total companies analyzed: 6
High-risk companies (score >= 60): 2
------------------------------------------------------------

HIGH RISK COMPANIES:

1. AMC Entertainment Holdings Inc (AMC)
   Risk Score: 78/100 [High]
   Confidence: High
   Key Risk Factors:
     • High debt-to-equity ratio
     • Negative free cash flow
     • Declining revenue trend

2. GameStop Corp (GME)
   Risk Score: 72/100 [High]
   Confidence: Medium
   Key Risk Factors:
     • Significant price volatility
     • Negative news sentiment
     • Weak profitability metrics
```

## Next Steps

### Analyze Different Companies

Edit `config/config.yaml`:

```yaml
companies:
  test_set:
    - "AAPL"  # Apple
    - "MSFT"  # Microsoft
    - "NVDA"  # NVIDIA
    # Add any US or Chinese stocks
```

Then run: `python main.py`

### Try Different Examples

```bash
# Run interactive examples
python example.py

# Options:
# 1. Analyze single company
# 2. Batch analysis
# 3. Generate watchlist
# 4. Custom company list
# 5. Run all examples
```

### Use in Your Code

```python
from src.pipeline import CreditRiskPredictor
import yaml

# Load config
with open('config/config.yaml') as f:
    config = yaml.safe_load(f)

# Initialize
predictor = CreditRiskPredictor(config)

# Analyze a company
result = predictor.predict_risk("TSLA")
print(f"Risk Score: {result['risk_score']}/100")

# Analyze multiple companies
tickers = ["TSLA", "NIO", "BABA"]
results = predictor.predict_batch(tickers)

# Generate watchlist
watchlist = predictor.generate_watchlist(tickers, threshold=60)
```

## Configuration Options

### Change LLM Provider

Edit `config/config.yaml`:

```yaml
llm:
  provider: "anthropic"  # or "openai"
  model: "claude-3-sonnet-20240229"  # or "gpt-4"
  temperature: 0.1
  max_tokens: 2000
```

### Adjust Risk Threshold

```yaml
prediction:
  risk_threshold: 0.7  # Higher = only flag very high risk
  prediction_horizon: 7  # Predict next 7 days
```

### Customize Data Collection

```yaml
data_sources:
  news:
    max_articles: 30  # Get more news articles
    days_lookback: 14  # Look further back
```

## Troubleshooting

### "No API key found"
- Make sure `.env` file exists in project root
- Check that API key is correctly formatted
- Verify no extra spaces in `.env` file

### "No data available for ticker"
- Check ticker symbol is correct (use Yahoo Finance format)
- Some companies may have limited data
- Try a well-known stock like "AAPL" or "TSLA"

### "Import error"
- Ensure virtual environment is activated
- Run `uv pip install -e .` again
- Check Python version is 3.12+

### Rate Limiting
- If analyzing many companies, add delays between requests
- Consider using cheaper models (gpt-3.5-turbo) for testing

## Understanding Risk Scores

- **0-20 (Very Low)**: Strong fundamentals, positive outlook
- **21-40 (Low)**: Stable company with minimal concerns
- **41-60 (Moderate)**: Some risk factors, needs monitoring
- **61-80 (High)**: Significant risk factors, careful review needed
- **81-100 (Very High)**: Multiple severe issues, high default risk

## Tips for Best Results

1. **Start with well-known companies**: Test with large-cap stocks first
2. **Review the reasoning**: LLM provides explanations - read them!
3. **Cross-reference**: Compare with traditional metrics (Z-Score, etc.)
4. **Consider context**: Industry and market conditions matter
5. **Use multiple data points**: Don't rely on single metric

## Next: Deep Dive

For detailed information, see:
- `README.md` - Full documentation
- `example.py` - More usage examples
- `config/config.yaml` - All configuration options

## Getting Help

- Check documentation in `README.md`
- Review example code in `example.py`
- Open an issue on GitHub

Happy risk analyzing! 📊
