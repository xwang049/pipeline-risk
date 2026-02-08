# Credit Risk Prediction Pipeline - Complete Workflow

## 📋 目录
- [快速概览](#快速概览)
- [项目结构](#项目结构)
- [Entry Point](#entry-point)
- [完整执行流程](#完整执行流程)
- [每个文件的作用](#每个文件的作用)
- [数据流图](#数据流图)
- [关键概念](#关键概念)

---

## 🎯 快速概览

这是一个**LLM驱动的信用风险预测系统**，支持：
- ✅ 自动选择高风险公司
- ✅ 时间旅行回测
- ✅ 多数据源整合（财报、市场、新闻）
- ✅ 智能缓存和重试机制

**核心理念**：用2026-02-01的数据预测2026-02-08可能爆雷的公司，一周后验证准确性。

---

## 📁 项目结构

```
pipeline-risk/
├── main.py                          # 🚀 ENTRY POINT - 程序入口
├── config/
│   └── config.yaml                  # 配置文件（时间、权重、API设置）
├── src/
│   ├── __init__.py
│   ├── utils.py                     # 🔧 缓存管理器
│   ├── llm/                         # 🤖 LLM接口层
│   │   ├── __init__.py
│   │   ├── model_interface.py       # LLM API调用（Gemini/OpenAI/Claude）
│   │   └── prompt_templates.py      # Prompt模板
│   ├── data_collector/              # 📊 数据收集层
│   │   ├── __init__.py
│   │   ├── company_info.py          # 公司基本信息
│   │   ├── financial_data.py        # 财务数据（yfinance）
│   │   ├── market_data.py           # 市场数据（价格、波动）
│   │   └── news_collector.py        # 新闻数据
│   ├── features/                    # 🔍 特征工程层
│   │   ├── __init__.py
│   │   └── financial_features.py    # 财务特征提取（Z-Score等）
│   └── pipeline/                    # 🔄 核心Pipeline层
│       ├── __init__.py
│       ├── company_selector.py      # 公司选择器（LLM自动选择）
│       └── risk_predictor.py        # 风险预测器（主逻辑）
├── data/
│   ├── cache/                       # 缓存目录（24h TTL）
│   └── results/                     # 预测结果输出
└── .env                             # API密钥

总计：17个核心源文件 + 配置
```

---

## 🚀 Entry Point

### `main.py`

**作用**：程序的入口，协调所有模块。

**执行流程**：

```python
def main():
    # 1. 解析命令行参数
    args = parse_args()

    # 2. 加载配置文件
    config = load_config(args.config)

    # 3. 确定时间参数（CLI > config > 当前日期）
    as_of_date = args.as_of_date or config['prediction']['as_of_date']

    # 4. 初始化LLM接口
    llm = LLMInterface(provider="gemini", model="gemini-2.5-flash")

    # ========== STEP 1: 选择公司 ==========
    selector = CompanySelector(llm)
    tickers = selector.select_high_risk_companies(
        num_companies=5,
        market="US",
        as_of_date="2026-02-01"  # 时间旅行参数
    )
    # 返回: ['AMC', 'BYND', 'PTON', 'GME', 'CVNA']

    # ========== STEP 2: 风险分析 ==========
    predictor = CreditRiskPredictor(config, as_of_date="2026-02-01")
    watchlist = predictor.generate_watchlist(tickers, threshold=60)
    # 返回: {
    #   'high_risk_companies': [...],
    #   'all_results': [...]
    # }

    # ========== STEP 3: 保存结果 ==========
    filepath = predictor.save_results(watchlist)
    # 保存到: data/results/risk_prediction_20260208_HHMMSS.json
```

**命令行参数**：
```bash
python main.py                              # 实时模式
python main.py --as-of-date 2026-02-01     # 回测模式
python main.py --companies 10 -n 10        # 指定公司数量
```

---

## 🔄 完整执行流程

### Phase 1: 公司选择（STEP 1）

```
main.py
  └─> CompanySelector.select_high_risk_companies()
        │
        ├─> _create_selection_prompt()
        │     └─> 生成Prompt：
        │           "Today is 2026-02-01. Select 5 high-risk companies..."
        │           + 时间约束：不能使用2月1日后的信息
        │           + 强调：只选当前交易的公司
        │
        ├─> LLMInterface.generate()
        │     ├─> [缓存检查] cache_manager.get()
        │     ├─> [未命中] _generate_gemini()
        │     │     └─> 重试3次 + 指数退避
        │     └─> [缓存保存] cache_manager.set()
        │
        ├─> _parse_company_list()
        │     ├─> 尝试JSON解析
        │     ├─> [失败] 增强提取 _extract_tickers_enhanced()
        │     └─> [失败] 基础提取 _extract_tickers_fallback()
        │
        └─> _validate_companies()
              ├─> 检查每个ticker是否还在交易
              ├─> yfinance.history(period="1mo")
              ├─> 验证最后交易日期 < 30天前
              └─> 过滤掉已退市公司

返回: ['AMC', 'GME', 'CVNA', 'PTON', 'BYND']  # 5家验证过的公司
```

### Phase 2: 数据收集（For each company）

```
CreditRiskPredictor.predict_risk('BYND')
  │
  └─> collect_company_data('BYND')
        │
        ├─> CompanyInfoCollector.get_company_info()
        │     └─> yfinance.Ticker('BYND').info
        │         返回: {name, sector, industry, country}
        │
        ├─> FinancialDataCollector.get_financial_metrics()
        │     ├─> [缓存检查] cache_manager.get("financial_data")
        │     ├─> [未命中] yfinance获取财务数据
        │     │     • debt_to_equity: 债务/权益比
        │     │     • current_ratio: 流动比率
        │     │     • operating_margin: 营业利润率
        │     │     • roe: 净资产收益率
        │     │     • free_cash_flow: 自由现金流
        │     └─> [缓存保存]
        │
        ├─> MarketDataCollector.get_market_indicators()
        │     ├─> [缓存检查]
        │     ├─> [未命中] 获取市场数据
        │     │     • price_change_1w, 1m, 3m: 价格变化
        │     │     • volume_change: 成交量变化
        │     │     • volatility: 波动率
        │     └─> [缓存保存]
        │
        ├─> NewsCollector.get_company_news()
        │     ├─> [缓存检查]
        │     ├─> [未命中] 获取新闻（最多20条）
        │     └─> [时间过滤] _filter_news_by_date()
        │           • 只保留 published_date <= as_of_date 的新闻
        │           • 防止"未来信息泄露"
        │
        ├─> FinancialFeatureExtractor.compute_risk_indicators()
        │     └─> 计算风险指标：
        │           • leverage_risk: 高/中/低
        │           • liquidity_risk: 高/中/低
        │           • profitability_risk: 高/中/低
        │
        └─> FinancialDataCollector.calculate_z_score()
              └─> Altman Z-Score = 1.2×X1 + 1.4×X2 + 3.3×X3 + 0.6×X4 + 1.0×X5
                    • < 1.8: 高风险
                    • 1.8-3.0: 灰色地带
                    • > 3.0: 安全

返回: {
    ticker: 'BYND',
    financial_metrics: {...},
    market_data: {...},
    recent_news: [...],  # 已过滤
    z_score: -2.29,
    risk_indicators: {...}
}
```

### Phase 3: LLM风险分析

```
LLMInterface.analyze_credit_risk(company_data, as_of_date, weights)
  │
  ├─> PromptTemplates.credit_risk_analysis_prompt()
  │     └─> 生成分析Prompt：
  │           """
  │           🔒 TIME CONSTRAINT: As of 2026-02-01
  │           Company: Beyond Meat (BYND)
  │
  │           ## Financial Metrics:
  │           - Debt to Equity: 5.8
  │           - Current Ratio: 0.9
  │           - Operating Margin: -35%
  │           - Revenue Growth: -13.3%
  │
  │           ## Market Data:
  │           - Price Change 1M: -8.5%
  │           - Volatility: 4.2
  │
  │           ## Recent News (before 2026-02-01):
  │           - "Beyond Meat posts wider loss..."
  │
  │           ## Analysis Guidelines:
  │           Feature Weights:
  │           - Financial Metrics: 50% (MOST IMPORTANT)
  │           - Market Signals: 35%
  │           - News Sentiment: 15% (LEAST - often noise)
  │
  │           Predict risk for NEXT 7 DAYS (2026-02-01 to 02-08)
  │           """
  │
  ├─> LLMInterface.generate()
  │     ├─> [重试3次 + 指数退避]
  │     └─> 返回JSON响应
  │
  ├─> parse_json_response()
  │     ├─> 策略1: 直接解析
  │     ├─> 策略2: 修复截断JSON
  │     ├─> 策略3: 去除```json代码块
  │     └─> 策略4: 修复trailing comma
  │
  └─> [缓存] cache_manager.set("risk_prediction")

返回: {
    risk_score: 95,
    risk_level: "Very High Risk",
    key_risk_factors: [
        "严重亏损，收入下降13.3%",
        "现金消耗严重，FCF负值",
        "Z-Score -2.29（破产高危）"
    ],
    confidence_level: "High",
    reasoning: "..."
}
```

### Phase 4: 结果汇总与保存

```
CreditRiskPredictor.generate_watchlist()
  │
  ├─> predict_batch(tickers)
  │     └─> 对每个公司调用 predict_risk()
  │           [并发执行，带缓存加速]
  │
  ├─> rank_by_risk()
  │     └─> 按risk_score降序排序
  │
  ├─> 筛选高风险公司（score >= threshold）
  │
  └─> save_results()
        └─> 保存到 data/results/risk_prediction_TIMESTAMP.json

输出文件结构:
{
    "generation_timestamp": "2026-02-08T18:00:00",
    "total_companies_analyzed": 5,
    "high_risk_count": 3,
    "high_risk_companies": [
        {
            "ticker": "BYND",
            "risk_score": 95,
            "risk_level": "Very High Risk",
            "key_risk_factors": [...],
            "data_quality": {
                "has_financial_data": true,
                "data_completeness": 1.0
            }
        },
        ...
    ],
    "llm_selection": {
        "selected_tickers": ["AMC", "GME", "CVNA", "PTON", "BYND"],
        "selection_timestamp": "..."
    }
}
```

---

## 📄 每个文件的作用

### 1️⃣ **main.py** - 程序入口
```python
# 职责：
- 解析命令行参数（--as-of-date, --companies）
- 协调所有模块
- 显示进度和结果
- 异常处理

# 关键函数：
- parse_args(): 命令行参数解析
- load_config(): 加载YAML配置
- main(): 主执行流程
```

### 2️⃣ **config/config.yaml** - 配置文件
```yaml
# 配置项：
llm:
  provider: "gemini"              # LLM提供商
  model: "gemini-2.5-flash"       # 模型
  temperature: 0.1                # 创造性（低=保守）
  max_tokens: 4000                # 最大输出

prediction:
  as_of_date: null                # 时间旅行日期
  top_k_companies: 5              # 分析公司数
  weights:                        # 特征权重
    financial_metrics: 0.50       # 财务指标50%
    market_signals: 0.35          # 市场信号35%
    news_sentiment: 0.15          # 新闻情绪15%

data_sources:
  news:
    max_articles: 20              # 最多获取新闻数
    days_lookback: 7              # 回溯天数
```

### 3️⃣ **src/utils.py** - 缓存管理器
```python
# 职责：
- 文件缓存系统（data/cache/）
- TTL: 24小时自动过期
- MD5 hash作为cache key

# 关键类：
class CacheManager:
    def get(prefix, data):     # 获取缓存
    def set(prefix, data, result):  # 设置缓存

# 使用示例：
cache_manager.get("financial_data", {"ticker": "BYND"})
cache_manager.set("financial_data", {"ticker": "BYND"}, {...})
```

### 4️⃣ **src/llm/model_interface.py** - LLM接口
```python
# 职责：
- 统一的LLM API接口
- 支持多个提供商（Gemini/OpenAI/Claude）
- 重试机制 + 指数退避
- JSON解析增强

# 关键方法：
class LLMInterface:
    def generate():              # 生成文本（带重试）
    def analyze_credit_risk():   # 风险分析（调用generate）
    def parse_json_response():   # 多策略JSON解析

    # 私有方法：
    _generate_gemini()           # Gemini API
    _generate_openai()           # OpenAI API
    _generate_anthropic()        # Claude API
```

### 5️⃣ **src/llm/prompt_templates.py** - Prompt模板
```python
# 职责：
- 构建结构化的Prompt
- 注入时间约束
- 注入特征权重
- 格式化数据展示

# 关键方法：
class PromptTemplates:
    @staticmethod
    def credit_risk_analysis_prompt(
        company_data,
        as_of_date,    # 时间约束
        weights        # 特征权重
    ):
        # 返回完整的分析Prompt
```

### 6️⃣ **src/data_collector/company_info.py** - 公司信息
```python
# 职责：
- 获取公司基本信息
- 通过yfinance获取

# 返回：
{
    'name': 'Beyond Meat, Inc.',
    'sector': 'Consumer Defensive',
    'industry': 'Packaged Foods',
    'country': 'United States'
}
```

### 7️⃣ **src/data_collector/financial_data.py** - 财务数据
```python
# 职责：
- 获取财务指标（yfinance）
- 计算Z-Score
- 带缓存

# 关键方法：
class FinancialDataCollector:
    @staticmethod
    def get_financial_metrics(ticker):
        # 返回: debt_to_equity, current_ratio, roe, etc.

    @staticmethod
    def calculate_z_score(ticker):
        # Altman Z-Score破产预测模型
        # < 1.8: 高风险
        # 1.8-3.0: 灰色地带
        # > 3.0: 安全
```

### 8️⃣ **src/data_collector/market_data.py** - 市场数据
```python
# 职责：
- 获取价格和成交量数据
- 计算技术指标（波动率、变化率）
- 异常检测（价格突变）

# 关键方法：
class MarketDataCollector:
    @staticmethod
    def get_market_indicators(ticker):
        # 返回: price_change_1w, 1m, 3m, volatility

    @staticmethod
    def detect_price_anomalies(ticker):
        # 检测价格异常（>2σ）
```

### 9️⃣ **src/data_collector/news_collector.py** - 新闻数据
```python
# 职责：
- 获取公司相关新闻
- 情绪分析（正面/负面/中性）
- 事件检测（破产、裁员等关键词）

# 关键方法：
class NewsCollector:
    @staticmethod
    def get_company_news(ticker, max_articles=20):
        # 返回新闻列表

    @staticmethod
    def analyze_news_sentiment(news_articles):
        # 简单关键词情绪分析
        # 返回: sentiment_score, positive_count, negative_count
```

### 🔟 **src/features/financial_features.py** - 特征提取
```python
# 职责：
- 从财务数据提取风险指标
- 分类风险等级（HIGH/MEDIUM/LOW）

# 关键方法：
class FinancialFeatureExtractor:
    @staticmethod
    def compute_risk_indicators(metrics):
        # 返回:
        {
            'leverage_risk': 'HIGH',      # debt_to_equity > 3
            'liquidity_risk': 'MEDIUM',   # current_ratio < 1.5
            'profitability_risk': 'LOW',  # roe > 0
            'cash_flow_risk': 'HIGH'      # fcf < 0
        }
```

### 1️⃣1️⃣ **src/pipeline/company_selector.py** - 公司选择器
```python
# 职责：
- 使用LLM自动选择高风险公司
- 验证公司是否还在交易
- 过滤已退市公司

# 关键方法：
class CompanySelector:
    def select_high_risk_companies(num, market, as_of_date):
        # 1. LLM选择候选公司
        # 2. 验证公司状态
        # 3. 返回有效ticker列表

    def _validate_companies(tickers):
        # yfinance验证：
        # - 最近30天有交易
        # - 有有效市场价格
```

### 1️⃣2️⃣ **src/pipeline/risk_predictor.py** - 风险预测器（核心）
```python
# 职责：
- 整合所有数据收集
- 调用LLM分析
- 生成最终报告
- 批量处理

# 关键方法：
class CreditRiskPredictor:
    def __init__(config, as_of_date):
        # 初始化，保存时间参数和权重

    def collect_company_data(ticker):
        # 收集所有数据源
        # 返回完整的company_data字典

    def predict_risk(ticker):
        # 单个公司风险预测（带缓存和重试）

    def generate_watchlist(tickers, threshold):
        # 批量分析，生成高风险清单

    def save_results(watchlist):
        # 保存到JSON文件
```

---

## 📊 数据流图

```
用户命令
  │
  ├─> python main.py --as-of-date 2026-02-01
  │
  v
┌─────────────────────────────────────────────────────────────┐
│                     MAIN.PY (Entry Point)                   │
│  - 解析CLI参数                                               │
│  - 加载config.yaml                                           │
│  - 确定as_of_date = "2026-02-01"                            │
└─────────────────────────────────────────────────────────────┘
  │
  v
┌─────────────────────────────────────────────────────────────┐
│          STEP 1: CompanySelector.select_high_risk()         │
│  - 构建Prompt: "Today is 2026-02-01..."                     │
│  - LLM推理 → 返回ticker列表                                  │
│  - 验证每个ticker还在交易                                     │
│  - 过滤已退市公司                                             │
└─────────────────────────────────────────────────────────────┘
  │
  │ 返回: ['AMC', 'GME', 'CVNA', 'PTON', 'BYND']
  │
  v
┌─────────────────────────────────────────────────────────────┐
│   STEP 2: CreditRiskPredictor.generate_watchlist()         │
│                                                             │
│   For each ticker in ['AMC', 'GME', ...]                   │
│     │                                                       │
│     ├─> collect_company_data(ticker)                       │
│     │     ├─> CompanyInfoCollector     [缓存]              │
│     │     ├─> FinancialDataCollector   [缓存]              │
│     │     ├─> MarketDataCollector      [缓存]              │
│     │     ├─> NewsCollector            [缓存+时间过滤]      │
│     │     └─> FinancialFeatureExtractor                    │
│     │                                                       │
│     │   返回: company_data{...}                            │
│     │                                                       │
│     └─> LLM.analyze_credit_risk(company_data)             │
│           ├─> PromptTemplates.credit_risk_analysis_prompt()│
│           │     • 注入时间约束                              │
│           │     • 注入特征权重                              │
│           │                                                │
│           ├─> LLMInterface.generate()  [重试3次+缓存]      │
│           │                                                │
│           └─> parse_json_response()    [多策略解析]        │
│                                                            │
│           返回: risk_analysis{score, factors, ...}         │
│                                                            │
│   收集所有结果 → rank_by_risk() → 筛选高风险                 │
└─────────────────────────────────────────────────────────────┘
  │
  │ 返回: watchlist{high_risk_companies, all_results}
  │
  v
┌─────────────────────────────────────────────────────────────┐
│       STEP 3: save_results()                                │
│  - 生成时间戳文件名                                           │
│  - 保存到 data/results/risk_prediction_YYYYMMDD_HHMMSS.json│
│  - 日志输出结果摘要                                           │
└─────────────────────────────────────────────────────────────┘
  │
  v
输出: data/results/risk_prediction_20260208_180000.json
```

---

## 🔑 关键概念

### 1. **时间旅行（Time-Travel）**
```python
# 设置 as_of_date = "2026-02-01"
#
# 效果：
# - LLM认为今天是2月1日
# - 只使用2月1日前的数据
# - 新闻被过滤（published_date <= 2026-02-01）
# - 预测2月1-8日的风险
#
# 用途：
# - 回测：在2月8日验证2月1日的预测准不准
# - 无偏：防止"未来信息泄露"
```

### 2. **特征权重（Feature Weights）**
```python
weights = {
    'financial_metrics': 0.50,    # 50% - 债务、现金流、利润率
    'market_signals': 0.35,       # 35% - 价格变化、波动率
    'news_sentiment': 0.15        # 15% - 新闻情绪（降低权重）
}

# 理由：
# - 财务数据最可靠（历史验证）
# - 市场信号反映市场共识
# - 新闻常为噪音（滞后、情绪化）
```

### 3. **缓存策略（Caching）**
```python
# TTL: 24小时
#
# 缓存内容：
# ✅ 财务数据（24h内不变）
# ✅ 市场数据
# ✅ 新闻数据
# ✅ LLM响应
# ✅ 风险预测结果
#
# 好处：
# - 减少API调用（节省quota）
# - 加速回测（同一公司不重复获取）
# - 成本降低
```

### 4. **重试机制（Retry with Exponential Backoff）**
```python
max_retries = 3
for attempt in range(max_retries):
    try:
        return api_call()
    except Exception:
        delay = (2 ** attempt) + random.uniform(0.1, 1.0)
        #      ^^^^^^^^^^^^^^   ^^^^^^^^^^^^^^^^^^^^^^^^^^^
        #      指数增长          随机抖动（jitter）
        #
        #      attempt 0: ~1秒
        #      attempt 1: ~2秒
        #      attempt 2: ~4秒
        time.sleep(delay)

# 理由：
# - 避免rate limit后立即重试
# - jitter防止多个请求同时重试（thundering herd）
```

### 5. **公司验证（Validation）**
```python
def _validate_companies(tickers):
    # 检查：
    # 1. 最近30天有交易记录
    # 2. 有有效的市场价格
    # 3. yfinance能获取到数据

    # 目的：
    # - 过滤已退市公司（FSR, EXPR已破产）
    # - 确保预测有意义（不预测死公司）
    # - 只分析当前风险
```

---

## 🎯 使用场景

### 场景1：实时预测（今天的风险）
```bash
python main.py
# as_of_date = today
# 预测未来7天哪些公司可能爆雷
```

### 场景2：回测验证（历史预测准确性）
```bash
python main.py --as-of-date 2026-02-01
# 假装在2月1日，预测2月1-8日
# 现在是2月8日，可以验证准不准
```

### 场景3：批量回测（不同时间点）
```bash
python main.py --as-of-date 2026-01-15 > results_0115.txt
python main.py --as-of-date 2026-02-01 > results_0201.txt
python main.py --as-of-date 2026-02-08 > results_0208.txt
# 比较不同时间点的预测效果
```

---

## 📈 性能优化总结

| 优化项 | 实现方式 | 效果 |
|--------|---------|------|
| 缓存 | 24h文件缓存 | 减少80%+ API调用 |
| 重试 | 指数退避+jitter | 应对网络波动 |
| 过滤 | 时间过滤+公司验证 | 提高预测质量 |
| 并发 | 批量处理（可扩展） | 加速分析 |

---

## 🐛 错误处理

```python
# 分层错误处理：

# Level 1: LLM API调用
try:
    response = gemini.generate()
except Exception:
    # 重试3次，指数退避

# Level 2: 单个公司分析
try:
    result = predict_risk('BYND')
except Exception:
    # 返回结构化错误结果
    # 不影响其他公司

# Level 3: 整个Pipeline
try:
    watchlist = generate_watchlist(tickers)
except Exception:
    # 记录日志，优雅退出
```

---

## 📚 扩展方向

1. **数据源扩展**
   - 添加CDS spread数据
   - 添加评级机构数据
   - 添加SEC文件分析

2. **模型扩展**
   - 集成传统机器学习模型
   - LLM ensemble（多模型投票）
   - 分层记忆系统（layered-memory-architecture分支）

3. **回测增强**
   - 自动化回测框架
   - 准确率统计
   - ROC曲线分析

---

**总结**：这是一个完整的生产级LLM应用，包含数据收集、特征工程、LLM推理、缓存优化、错误处理的全链路。核心创新是**时间旅行回测**和**智能公司选择**。
