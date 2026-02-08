# Benchmark Framework Quick Start

## What's New?

This branch introduces a **professional benchmark architecture** inspired by HELM, FinGPT, and FinBench.

### Key Features

✅ **Multi-Data Source Support**
- Yahoo Finance (financial + market data)
- News API (sentiment analysis)
- Local Knowledge Base (RAG) - coming soon
- Lab Database - ready for integration

✅ **Multi-LLM Provider Support**
- OpenAI (gpt-4o-mini)
- Google Gemini (gemini-2.5-flash)
- Easy to add more

✅ **Modular & Extensible**
- Plug-in architecture
- Add new data sources without changing core code
- Configuration-driven

✅ **Cost & Performance Tracking**
- Automatic token counting
- Cost calculation per provider
- Latency tracking

---

## Quick Start

### 1. Install Dependencies

```bash
uv sync
```

### 2. Run Benchmark

```bash
# Simple run (uses Gemini by default)
python scripts/run_benchmark.py

# Compare providers
python scripts/run_benchmark.py --providers openai gemini

# Time-travel backtesting
python scripts/run_benchmark.py --as-of-date 2026-02-01

# Analyze fewer companies (save API quota)
python scripts/run_benchmark.py --num-companies 3
```

### 3. View Results

Results are saved to `experiments/runs/` with detailed statistics:
- Risk scores for each company
- LLM costs and token usage
- Execution time
- Success rates

---

## Architecture

```
BenchmarkRunner
├── Scenario (CreditRiskScenario)
│   ├── Company Selection (LLM or manual)
│   └── Data Collection
│       ├── Yahoo Finance
│       ├── News API
│       ├── Local KB (future)
│       └── Lab DB (future)
├── Adapter (OpenAI/Gemini/...)
│   └── LLM API calls + tracking
└── Results
    ├── Risk predictions
    ├── Cost tracking
    └── Performance metrics
```

---

## Configuration

### Scenario Config: `config/scenarios/credit_risk.yaml`

```yaml
scenario:
  selection_mode: auto  # LLM selects companies
  num_companies: 5
  market: US

  # Time-travel for backtesting
  as_of_date: null  # or "2026-02-01"

  # Feature weights
  weights:
    financial_metrics: 0.50
    market_signals: 0.35
    news_sentiment: 0.15

  # Data sources
  data_sources:
    - type: yahoo
      enabled: true
    - type: news
      enabled: true
    - type: local_kb
      enabled: false  # Enable when KB is ready
    - type: lab_db
      enabled: false  # Enable when access granted
```

### LLM Config: `config/config.yaml`

```yaml
llm:
  provider: gemini
  model: models/gemini-2.5-flash
  temperature: 0.1
  max_tokens: 2000
```

---

## Adding New Data Sources

### Step 1: Implement DataSource Interface

```python
from src.data.base import DataSource, DataInstance

class MyDataSource(DataSource):
    def fetch(self, query, as_of_date=None):
        # Your implementation
        data = fetch_from_api(query['ticker'])
        return [DataInstance(
            id=f"{query['ticker']}_my_source",
            data=data,
            source=self.source_type
        )]

    def validate(self):
        return True  # Check if source is available

    @property
    def source_type(self):
        return "custom:mysource"
```

### Step 2: Register

```python
from src.data.registry import DataSourceRegistry
DataSourceRegistry.register("mysource", MyDataSource)
```

### Step 3: Enable in Config

```yaml
data_sources:
  - type: mysource
    enabled: true
    config:
      api_key: xxx
```

---

## Adding New LLM Providers

### Step 1: Implement LLMAdapter

```python
from src.adapters.base import LLMAdapter, LLMRequest, LLMResponse

class MyLLMAdapter(LLMAdapter):
    def generate(self, request: LLMRequest) -> LLMResponse:
        # Call your LLM
        response = self.client.chat(request.prompt)
        return LLMResponse(
            text=response.text,
            tokens_used=response.tokens,
            latency_ms=...,
            cost_usd=self._calculate_cost(response.tokens),
            model=self.model,
            provider="myprovider"
        )

    @property
    def provider_name(self):
        return "myprovider"
```

### Step 2: Register

```python
from src.adapters.factory import AdapterFactory
AdapterFactory.register("myprovider", MyLLMAdapter)
```

---

## Backward Compatibility

**Old code still works!**

```bash
# Old entry point (preserved)
python main.py

# New benchmark framework
python scripts/run_benchmark.py
```

Both use the same underlying data collectors and LLM interfaces.

---

## Roadmap

### ✅ Phase 1 (Complete)
- Data source abstraction layer
- LLM adapter system
- Scenario framework
- Benchmark runner

### 🔨 Phase 2 (In Progress)
- Metrics framework (F1, VaR, etc.)
- MLflow/WandB integration
- Anthropic adapter

### ⏳ Phase 3 (Planned)
- Local knowledge base (RAG)
- Lab database integration
- Ground truth evaluation
- Web UI for results

---

## Documentation

- **Architecture**: [docs/ARCHITECTURE.md](ARCHITECTURE.md)
- **Workflow**: [WORKFLOW.md](../WORKFLOW.md)
- **Deployment**: [PREFECT_DEPLOYMENT.md](../PREFECT_DEPLOYMENT.md)

---

## Key Design Patterns

- **Strategy Pattern**: LLMAdapter (swap providers)
- **Factory Pattern**: AdapterFactory, DataSourceRegistry
- **Registry Pattern**: Plug-in architecture
- **Dependency Injection**: Cache manager
- **Immutable Objects**: Reproducibility

---

## Comparison: Old vs New

| Aspect | Old (`main.py`) | New (Benchmark) |
|--------|-----------------|-----------------|
| **Entry Point** | `main.py` | `scripts/run_benchmark.py` |
| **Data Sources** | Hardcoded | Configurable + extensible |
| **LLM Providers** | Hardcoded switch | Factory pattern |
| **Multi-Provider** | Sequential runs | Parallel comparison |
| **Cost Tracking** | Manual | Automatic |
| **Extensibility** | Modify core code | Plug-in architecture |
| **Configuration** | Single YAML | Hierarchical configs |

---

## Example Output

```
==================================================================
Credit Risk Prediction Benchmark - Professional Architecture
==================================================================
Date: 2026-02-08 20:00:00
Config: config/scenarios/credit_risk.yaml
Providers: gemini
==================================================================

Initializing data sources...
✓ Enabled data source: financial:yahoo
✓ Enabled data source: news:api
Enabled 2 data sources

Creating run specifications...
✓ Created run spec for gemini
Created 1 run specifications

==================================================================
Run 1/1: gemini_credit_risk_prediction
==================================================================
Step 1: Generating evaluation instances
Generated 5 instances

Step 2: Running predictions
  AMC: Risk=75/100 (High)
  GME: Risk=70/100 (High)
  BYND: Risk=85/100 (Very High)
  PLUG: Risk=65/100 (High)
  NIO: Risk=60/100 (Moderate)

==================================================================
EXECUTION SUMMARY
==================================================================
Duration: 45.2s
Companies analyzed: 5
Successful predictions: 5
High-risk companies (≥60): 5

LLM Statistics:
  Total requests: 6
  Tokens used: 12,450
  Total cost: $0.0012
  Success rate: 100.0%
==================================================================
```

---

## Support

For questions or issues:
1. Check [docs/ARCHITECTURE.md](ARCHITECTURE.md)
2. Review example configs in `config/scenarios/`
3. Examine source code with inline documentation
