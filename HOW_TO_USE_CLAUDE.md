# 🤖 如何使用 Claude API

## 步骤 1：获取 Anthropic API Key

如果你还没有 API key：

1. 访问 https://console.anthropic.com/
2. 注册/登录账号
3. 进入 API Keys 页面
4. 创建新的 API key
5. 复制 key（格式：`sk-ant-api03-...`）

## 步骤 2：配置 API Key

编辑项目根目录的 `.env` 文件：

```bash
# 用真实的key替换下面这行
ANTHROPIC_API_KEY=sk-ant-api03-你的真实密钥在这里
```

保存文件。

## 步骤 3：运行测试

```bash
# 激活虚拟环境（如果还没激活）
source .venv/Scripts/activate

# 运行Claude测试脚本
python test_claude.py
```

## 期望输出

```
============================================================
Testing Claude API Connection
============================================================

Loading configuration...
LLM Provider: anthropic
Model: claude-3-5-sonnet-20241022

Initializing Credit Risk Predictor...
✓ Predictor initialized successfully

============================================================
Analyzing TSLA with Claude API
============================================================

Step 1/3: Collecting data for TSLA...
✓ Data collected: Tesla, Inc
  - Sector: Consumer Cyclical
  - Financial metrics: 15 items
  - Market data: 10 items
  - News articles: 20 articles

Step 2/3: Sending data to Claude for risk analysis...
(This may take 10-30 seconds...)
✓ Analysis complete!

============================================================
Risk Assessment Results for TSLA
============================================================

Company: Tesla, Inc
Ticker: TSLA

────────────────────────────────────────────────────────────
Risk Score: 52/100
Risk Level: Moderate
Confidence: High
────────────────────────────────────────────────────────────

Key Risk Factors:
  1. High valuation metrics relative to traditional automakers
  2. Competitive pressure in EV market intensifying
  3. Execution risk on multiple product launches

Early Warning Signals:
  1. Margin compression in recent quarters
  2. Increased competition from legacy automakers

Adverse Event Probabilities:
  - Rating Downgrade: 25.0%
  - Price Drop 20pct: 35.0%
  - Liquidity Issues: 15.0%
  - Default Risk: 5.0%

Analysis Reasoning:
  Tesla maintains strong brand position and innovation leadership
  in the EV space, but faces growing competitive pressures...

✅ Claude API Test Successful!
```

## Prompt 在哪里？

**文件位置：`src/llm/prompt_templates.py`**

主要的prompt模板在 `credit_risk_analysis_prompt()` 方法中（第32-90行）。

### Prompt 结构：

```python
prompt = f"""
You are a senior credit risk analyst.
Analyze the following company and predict its credit risk for the next 7 days.

Company: {name} ({ticker})

## Financial Metrics:
{财务指标数据}

## Market Data:
{市场数据}

## Recent News (Last 7 Days):
{近期新闻}

## Analysis Required:
1. Risk Score (0-100)
2. Key Risk Factors
3. Early Warning Signals
4. Probability of Adverse Event
5. Confidence Level

Please provide your analysis in JSON format...
"""
```

### 如何修改 Prompt？

编辑 `src/llm/prompt_templates.py` 文件：

```python
# 第32行开始，你可以修改：
# 1. 角色设定："You are a senior credit risk analyst"
# 2. 分析要求：添加更多分析维度
# 3. 输出格式：调整JSON结构
# 4. 评分标准：改变风险等级定义
```

例如，如果你想让Claude更关注中国市场：

```python
prompt = f"""You are a senior credit risk analyst specializing in
Chinese and Asian markets. Analyze the following company...

Consider:
- Regulatory risks in China
- Supply chain dependencies
- Cross-border payment risks
...
"""
```

## 使用不同的 Claude 模型

编辑 `config/config.yaml`：

```yaml
llm:
  provider: "anthropic"
  model: "claude-3-5-sonnet-20241022"  # 最新的 Sonnet 3.5
  # 或使用其他模型：
  # model: "claude-3-opus-20240229"     # 更强大但更贵
  # model: "claude-3-haiku-20240307"    # 更快更便宜
  temperature: 0.1
  max_tokens: 4000
```

## 分析不同公司

修改 `test_claude.py` 第75行：

```python
# 改成你想分析的公司
ticker = "AAPL"  # Apple
# ticker = "BABA"  # 阿里巴巴
# ticker = "NIO"   # 蔚来
# ticker = "PDD"   # 拼多多
```

然后重新运行：
```bash
python test_claude.py
```

## 批量分析多家公司

运行主程序（会分析config.yaml中的所有公司）：

```bash
python main.py
```

或者使用交互式示例：

```bash
python example.py
```

## API 费用参考

Claude 3.5 Sonnet 定价：
- Input: $3 / million tokens
- Output: $15 / million tokens

每家公司分析大约：
- Input: ~2,000 tokens（公司数据）
- Output: ~500 tokens（分析结果）
- 成本：约 $0.01-0.02 per company

100家公司 ≈ $1-2 USD

## 常见问题

### Q: API key 无效？
检查：
1. Key 格式正确（以 `sk-ant-api03-` 开头）
2. `.env` 文件中没有多余空格
3. API key 有额度（需要充值）

### Q: 请求超时？
1. 检查网络连接
2. 某些地区可能需要代理
3. 增加 timeout（在 model_interface.py 中）

### Q: 想要更详细的分析？
修改 `config/config.yaml`：
```yaml
llm:
  max_tokens: 8000  # 增加输出长度
  temperature: 0.2   # 稍微提高创造性
```

### Q: 如何保存完整对话？
结果会自动保存在 `data/results/` 目录，包含：
- 完整的 prompt
- Claude 的分析
- 所有数据
- 时间戳

## 下一步

1. ✅ 测试通过后，试着修改 prompt
2. ✅ 分析你关心的公司
3. ✅ 对比不同模型的结果
4. ✅ 查看 `example.py` 学习更多用法

祝使用愉快！🚀
