# Credit Risk Prediction Pipeline 🚀

**LLM + Knowledge Graph for Credit Risk Assessment**

A sophisticated credit risk prediction system that combines Large Language Models (LLMs) with financial data analysis to predict company default risk and credit rating changes.

## 🎯 Overview

This pipeline predicts credit risk for publicly traded companies by analyzing:
- **Financial Metrics**: Balance sheet, income statement, cash flow data
- **Market Data**: Stock price movements, volatility, trading volume
- **News Sentiment**: Recent news articles and their sentiment
- **Traditional Indicators**: Altman Z-Score, risk ratios

The system uses LLMs (GPT-4, Claude) to synthesize multiple data sources and generate risk assessments with explanations.

## ✨ Features

- 🔍 **Multi-source Data Collection**: Automatically gathers financial, market, and news data
- 🤖 **LLM-powered Analysis**: Uses state-of-the-art language models for risk assessment
- 📊 **Traditional Risk Metrics**: Includes Altman Z-Score and financial ratios
- 📰 **News Sentiment Analysis**: Analyzes recent news for risk signals
- 🎯 **Risk Ranking**: Ranks companies by predicted risk level
- 💾 **Result Export**: Saves detailed analysis in JSON format

## 🚀 Quick Start

### 1. Setup Environment

```bash
# Clone the repository
git clone <your-repo-url>
cd pipeline-risk

# Create and activate virtual environment with uv
uv venv
source .venv/Scripts/activate  # On Windows
# source .venv/bin/activate    # On macOS/Linux

# Install dependencies
uv pip install -e .
```

### 2. Configure API Keys

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` and add your API keys:

```
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

### 3. Configure Companies to Analyze

Edit `config/config.yaml` to specify companies:

```yaml
companies:
  test_set:
    - "TSLA"   # Tesla
    - "BABA"   # Alibaba
    - "NIO"    # NIO
    - "BIDU"   # Baidu
    - "AMC"    # AMC Entertainment
```

### 4. Run the Pipeline

```bash
python main.py
```

## 📁 Project Structure

```
pipeline-risk/
├── src/
│   ├── data_collector/       # Data collection modules
│   │   ├── company_info.py   # Company basic info
│   │   ├── financial_data.py # Financial metrics & Z-Score
│   │   ├── market_data.py    # Stock price & market data
│   │   └── news_collector.py # News articles & sentiment
│   ├── features/             # Feature engineering
│   │   └── financial_features.py
│   ├── llm/                  # LLM interface
│   │   ├── model_interface.py    # Unified LLM API
│   │   └── prompt_templates.py   # Risk analysis prompts
│   └── pipeline/             # Main pipeline
│       └── risk_predictor.py # Core prediction logic
├── config/
│   └── config.yaml           # Configuration file
├── data/
│   ├── raw/                  # Raw data
│   ├── processed/            # Processed data
│   └── results/              # Analysis results
├── main.py                   # Main entry point
└── README.md
```

## ⚙️ Configuration

Edit `config/config.yaml` to customize:

### LLM Settings

```yaml
llm:
  provider: "openai"          # Options: openai, anthropic
  model: "gpt-4"              # Model name
  temperature: 0.1            # Lower = more consistent
  max_tokens: 2000            # Response length
```

### Risk Prediction Settings

```yaml
prediction:
  lookback_days: 90           # Historical data window
  prediction_horizon: 7       # Predict next N days
  risk_threshold: 0.6         # High-risk threshold (0-1)
  top_k_companies: 20         # Top risky companies to report
```

## 📊 Output Format

The pipeline generates a JSON file with detailed analysis:

```json
{
  "generation_timestamp": "2024-02-06T12:00:00",
  "total_companies_analyzed": 6,
  "high_risk_count": 2,
  "high_risk_companies": [
    {
      "ticker": "AMC",
      "company_name": "AMC Entertainment Holdings Inc",
      "risk_score": 78,
      "risk_level": "High",
      "key_risk_factors": [
        "High debt-to-equity ratio",
        "Negative cash flow",
        "Declining revenue"
      ],
      "adverse_event_probabilities": {
        "rating_downgrade": 0.65,
        "price_drop_20pct": 0.55,
        "liquidity_issues": 0.70,
        "default_risk": 0.45
      },
      "confidence_level": "High",
      "reasoning": "Analysis shows multiple concerning signals..."
    }
  ]
}
```

## 🔬 Risk Assessment Methodology

### 1. Data Collection
- Financial metrics from company filings
- Real-time market data (price, volume, volatility)
- Recent news articles (last 7 days)
- Historical trends (90 days)

### 2. Traditional Analysis
- **Altman Z-Score**: Bankruptcy prediction model
- **Financial Ratios**: Debt/equity, current ratio, ROE, etc.
- **Price Anomalies**: Unusual price movements
- **News Sentiment**: Positive/negative news classification

### 3. LLM Synthesis
The LLM analyzes all collected data to:
- Assign risk score (0-100)
- Identify key risk factors
- Detect early warning signals
- Estimate probability of adverse events
- Provide reasoning and confidence level

### 4. Risk Ranking
Companies are ranked by risk score to identify the highest-risk entities.

## 🎓 Use Cases

### 1. Portfolio Risk Management
Monitor credit risk across your investment portfolio

### 2. Investment Research
Screen potential investments for credit risk

### 3. Academic Research
Study LLM capabilities in financial risk assessment

### 4. Benchmark Development
Build datasets for evaluating financial AI models

## 🔮 Future Enhancements

- [ ] **Knowledge Graph Integration**: Add company relationships and supply chain networks
- [ ] **Network Features**: Incorporate centrality, clustering coefficients
- [ ] **7B Local Models**: Support for Llama3-8B, Mistral-7B via Ollama
- [ ] **Multi-agent Architecture**: Separate agents for finance, news, and network analysis
- [ ] **Real-time Updates**: Continuous monitoring and daily risk reports
- [ ] **Backtesting**: Historical validation of predictions
- [ ] **Rating Agencies Integration**: Compare with Moody's, S&P, Fitch ratings
- [ ] **CDS Spread Data**: Incorporate credit default swap spreads

## 📝 Example Usage

### Analyze Specific Companies

```python
from src.pipeline import CreditRiskPredictor
import yaml

# Load config
with open('config/config.yaml') as f:
    config = yaml.safe_load(f)

# Initialize predictor
predictor = CreditRiskPredictor(config)

# Analyze single company
result = predictor.predict_risk("TSLA")
print(f"Risk Score: {result['risk_score']}/100")
print(f"Risk Level: {result['risk_level']}")

# Analyze multiple companies
tickers = ["TSLA", "BABA", "NIO"]
results = predictor.predict_batch(tickers)

# Generate watchlist
watchlist = predictor.generate_watchlist(tickers, threshold=60)
print(f"High-risk companies: {watchlist['high_risk_count']}")
```

## 🤝 Contributing

Contributions are welcome! Areas for improvement:
- Additional data sources (SEC filings, earnings calls)
- Enhanced NLP for news analysis
- Network graph construction
- Visualization dashboard
- Backtesting framework

## ⚠️ Disclaimer

This tool is for research and educational purposes only. It should not be used as the sole basis for investment decisions. Credit risk assessment requires professional judgment and should incorporate multiple sources of information.

## 📄 License

MIT License - see LICENSE file for details

## 🙏 Acknowledgments

- Built with OpenAI GPT-4 and Anthropic Claude
- Data from Yahoo Finance and public sources
- Inspired by academic research in financial AI and credit risk modeling
