# Benchmark Architecture Documentation

## Overview

This project implements a **professional LLM benchmark framework** for credit risk prediction, inspired by leading projects like **HELM** (Stanford), **FinGPT**, and **FinBench**.

**Key Design Principles:**
- **Modular**: Easy to add new data sources, LLM providers, and scenarios
- **Reproducible**: All states are serializable, configurations version-controlled
- **Extensible**: Plug-in architecture allows additions without modifying core code
- **Multi-source**: Supports local knowledge bases, web APIs, and future lab databases

---

## Architecture Components

```
┌────────────────────────────────────────────────────────┐
│                   BenchmarkRunner                      │
│              (Core Orchestrator)                       │
└──────────┬──────────────────┬─────────────────────────┘
           │                  │
   ┌───────▼──────┐    ┌─────▼──────┐
   │  Scenario    │    │  Adapter   │
   │  (Task+Data) │    │  (LLM API) │
   └───────┬──────┘    └────────────┘
           │
   ┌───────▼──────────────────┐
   │   DataSource Registry    │
   │ ┌─────┐ ┌─────┐ ┌─────┐  │
   │ │Yahoo│ │News │ │Local│  │
   │ │     │ │ API │ │ KB  │  │
   │ └─────┘ └─────┘ └─────┘  │
   │ ┌─────┐                   │
   │ │ Lab │ (future)          │
   │ │ DB  │                   │
   │ └─────┘                   │
   └───────────────────────────┘
```

---

## 1. Data Layer (`src/data/`)

### Base Classes

**DataSource** (Abstract Base Class)
- Interface for all data sources
- Methods: `fetch()`, `validate()`, `source_type`
- Supports time-travel via `as_of_date` parameter
- Cacheable for efficiency

**DataInstance** (Immutable Data Object)
- Represents a single piece of retrieved data
- Contains: id, data, metadata, timestamp, source
- Immutable for reproducibility

### Registry Pattern

**DataSourceRegistry**
- Central registry for data sources
- Dynamic registration: `DataSourceRegistry.register("yahoo", YahooFinanceSource)`
- Factory method: `DataSourceRegistry.create("yahoo", config)`

### Data Sources

| Source | Type | Status | Description |
|--------|------|--------|-------------|
| **YahooFinanceSource** | `financial:yahoo` | ✅ Implemented | Financial metrics, market data, Z-score |
| **NewsAPISource** | `news:api` | ✅ Implemented | Company news, sentiment, events |
| **LocalKnowledgeBase** | `knowledge_base:local` | 🔨 Placeholder | SQLite/Chroma for historical data (RAG) |
| **LabDatabaseSource** | `lab:database` | ⏳ Future | Lab proprietary database |

**Adding a New Data Source:**

```python
# 1. Implement DataSource interface
class MyCustomSource(DataSource):
    def fetch(self, query, as_of_date=None):
        # Your implementation
        pass

    def validate(self):
        return True

    @property
    def source_type(self):
        return "custom:mysource"

# 2. Register
DataSourceRegistry.register("mycustom", MyCustomSource)

# 3. Use in config
data_sources:
  - type: mycustom
    enabled: true
    config:
      api_key: xxx
```

---

## 2. Adapter Layer (`src/adapters/`)

### Base Classes

**LLMAdapter** (Abstract Base Class)
- Unified interface across LLM providers
- Methods: `generate()`, `batch_generate()`, `_calculate_cost()`
- Tracks: tokens used, cost, latency, success rate

**LLMRequest** (Immutable Request Object)
- Contains: prompt, system_prompt, temperature, max_tokens

**LLMResponse** (Immutable Response Object)
- Contains: text, tokens_used, latency_ms, cost_usd, error

### Adapters

| Provider | Model | Cost (est.) | Status |
|----------|-------|-------------|--------|
| **OpenAI** | gpt-4o-mini | $0.15/1M tokens | ✅ Implemented |
| **Gemini** | gemini-2.5-flash | Free (20/day) | ✅ Implemented |
| **Anthropic** | claude-3-5-haiku | $1/1M tokens | ⏳ TODO |

**Adding a New Adapter:**

```python
class MyLLMAdapter(LLMAdapter):
    def generate(self, request: LLMRequest) -> LLMResponse:
        # Call your LLM API
        response = self.client.generate(request.prompt)
        return LLMResponse(
            text=response.text,
            tokens_used=response.tokens,
            latency_ms=...,
            cost_usd=self._calculate_cost(response.tokens),
            model=self.model,
            provider=self.provider_name
        )

    @property
    def provider_name(self):
        return "myllm"

# Register
AdapterFactory.register("myllm", MyLLMAdapter)
```

---

## 3. Scenario Layer (`src/scenarios/`)

### CreditRiskScenario

Orchestrates the credit risk prediction workflow:

1. **Company Selection**
   - Auto mode: LLM selects high-risk companies
   - Manual mode: Use predefined list

2. **Data Collection**
   - Query all enabled data sources
   - Aggregate data into `ScenarioInstance`

3. **Instance Generation**
   - Create evaluation instances for each company
   - Support time-travel filtering

**Key Methods:**
- `get_instances()`: Generate evaluation instances
- `_select_companies()`: Select companies to analyze
- `_collect_company_data()`: Aggregate multi-source data

---

## 4. Core Layer (`src/core/`)

### BenchmarkRunner

Main orchestrator that executes benchmark runs.

**Workflow:**
```python
1. Initialize with RunSpec list
2. For each RunSpec:
   a. Get instances from scenario
   b. Run LLM predictions
   c. Collect metrics (cost, latency, accuracy)
   d. Save results
3. Generate summary statistics
```

**RunSpec:**
- Defines: scenario + adapter + config
- One RunSpec = One complete benchmark run

---

## Configuration System

### Hierarchical YAML Configuration

**`config/scenarios/credit_risk.yaml`** - Scenario-specific settings:
```yaml
scenario:
  selection_mode: auto  # or manual
  num_companies: 5
  market: US
  as_of_date: null  # or "2026-02-01" for backtesting

  weights:
    financial_metrics: 0.50
    market_signals: 0.35
    news_sentiment: 0.15

  data_sources:
    - type: yahoo
      enabled: true
      config:
        cache_ttl: 3600

    - type: local_kb
      enabled: false  # Enable when ready
```

**`config/config.yaml`** - Global LLM settings:
```yaml
llm:
  provider: gemini
  model: models/gemini-2.5-flash
  temperature: 0.1
  max_tokens: 2000
```

---

## Usage

### Quick Start

```bash
# Run with default config (Gemini)
python scripts/run_benchmark.py

# Compare multiple providers
python scripts/run_benchmark.py --providers openai gemini

# Time-travel backtesting
python scripts/run_benchmark.py --as-of-date 2026-02-01

# Custom config
python scripts/run_benchmark.py --config my_config.yaml
```

### Programmatic Usage

```python
from src.data.registry import DataSourceRegistry
from src.data.sources import YahooFinanceSource, NewsAPISource
from src.adapters import AdapterFactory
from src.scenarios.credit_risk import CreditRiskScenario
from src.core.runner import BenchmarkRunner, RunSpec

# Setup data sources
DataSourceRegistry.register('yahoo', YahooFinanceSource)
sources = [
    DataSourceRegistry.create('yahoo', config_yahoo),
    DataSourceRegistry.create('news', config_news),
]

# Setup adapter
adapter = AdapterFactory.create('openai', config_openai)

# Create scenario
scenario = CreditRiskScenario(config, sources, adapter)

# Create run spec
run_spec = RunSpec(scenario=scenario, adapter=adapter, config=config)

# Run benchmark
runner = BenchmarkRunner([run_spec])
results = runner.run()
```

---

## Extending the Framework

### Adding a New Scenario

```python
class MyScenario:
    def __init__(self, config, data_sources, llm):
        self.config = config
        self.data_sources = data_sources
        self.llm = llm

    def get_instances(self):
        # Generate evaluation instances
        pass

    @property
    def scenario_name(self):
        return "my_scenario"
```

### Adding a Knowledge Base

```python
# 1. Populate local knowledge base
import sqlite3
conn = sqlite3.connect('data/knowledge_base.db')
conn.execute("""
    CREATE TABLE company_fundamentals (
        ticker TEXT,
        report_date DATE,
        metrics JSON
    )
""")

# 2. Enable in config
data_sources:
  - type: local_kb
    enabled: true
    config:
      db_path: data/knowledge_base.db
```

### Adding Lab Database

```python
# 1. Implement LabDatabaseSource.fetch()
def fetch(self, query, as_of_date=None):
    import psycopg2
    conn = psycopg2.connect(...)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM lab_data WHERE ticker = %s", (query['ticker'],))
    # Return DataInstance objects

# 2. Enable in config
data_sources:
  - type: lab_db
    enabled: true
    config:
      host: lab.server.com
      database: company_data
```

---

## Migration from Old Code

### Backward Compatibility

**Old code still works!** The original `main.py` is preserved:

```bash
# Old way (still works)
python main.py --as-of-date 2026-02-01

# New way (benchmark framework)
python scripts/run_benchmark.py --as-of-date 2026-02-01
```

### Gradual Migration

1. **Phase 1**: Use new framework for experiments
2. **Phase 2**: Migrate main.py logic to scenarios
3. **Phase 3**: Deprecate old code

---

## Design Patterns Used

| Pattern | Where | Purpose |
|---------|-------|---------|
| **Strategy** | LLMAdapter | Swap LLM providers |
| **Factory** | AdapterFactory, DataSourceRegistry | Create objects dynamically |
| **Registry** | DataSourceRegistry | Plug-in architecture |
| **Template Method** | Scenario base class | Define workflow skeleton |
| **Dependency Injection** | Cache manager | Decouple components |
| **Immutable Objects** | DataInstance, LLMRequest | Reproducibility |

---

## Comparison with Leading Projects

| Feature | HELM | FinGPT | This Project |
|---------|------|--------|--------------|
| **Data Abstraction** | Scenario | Layered Pipeline | DataSource + Registry |
| **LLM Support** | 30+ models | API + LoRA | Adapter Factory |
| **Extensibility** | Plug-in | Modular Layers | Base Classes + Registry |
| **Time-Travel** | ✓ | ✓ | ✓ (as_of_date) |
| **Multi-Source** | ✓ | ✓ | ✓ (Yahoo, News, KB, Lab) |
| **Cost Tracking** | ✓ | ✗ | ✓ |
| **Experiment Tracking** | Custom DB | Versioning | MLflow (future) |

---

## Future Enhancements

### Phase 1 (Current)
- [x] Data source abstraction
- [x] LLM adapter system
- [x] Scenario framework
- [x] Benchmark runner

### Phase 2 (Next)
- [ ] Metrics framework (F1, MCC, VaR, CVaR)
- [ ] MLflow/WandB integration
- [ ] Ground truth evaluation
- [ ] Anthropic adapter

### Phase 3 (Future)
- [ ] Vector database (Chroma) for RAG
- [ ] Lab database integration
- [ ] Multi-scenario support
- [ ] Web UI for results visualization

---

## References

- **HELM**: [Holistic Evaluation of Language Models](https://crfm.stanford.edu/helm/)
- **FinGPT**: [Data-centric Financial LLM](https://github.com/AI4Finance-Foundation/FinGPT)
- **FinBench**: [Financial LLM Benchmark](https://arxiv.org/abs/2402.12659)

---

## Contact & Support

For questions or issues with the benchmark framework, see:
- Architecture documentation: `docs/ARCHITECTURE.md` (this file)
- Workflow documentation: `WORKFLOW.md`
- Deployment guide: `PREFECT_DEPLOYMENT.md`
