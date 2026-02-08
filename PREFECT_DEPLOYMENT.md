# Prefect 部署指南 / Prefect Deployment Guide

本文档介绍如何使用 Prefect 部署和运行每日信用风险预测流程。

## 1. 安装 Prefect

已包含在项目依赖中：

```bash
uv sync
```

## 2. 运行模式

### 2.1 本地测试运行（单次执行）

直接运行 Pipeline 进行测试：

```bash
python prefect_pipeline.py
```

**功能**：
- 立即执行一次完整的信用风险预测流程
- 不启动调度器
- 适合测试和调试

**输出**：
- 日志显示在终端
- 结果保存到 `data/results/risk_prediction_YYYYMMDD_HHMMSS.json`

### 2.2 部署为定时任务（生产模式）

启动 Prefect 调度器，每天早上 8:00 自动运行：

```bash
python prefect_pipeline.py serve
```

**功能**：
- 启动 Prefect 服务器和调度器
- 每天早上 8:00 (UTC+8) 自动执行
- 持续运行直到手动停止（Ctrl+C）

**配置**：
- Cron 表达式：`0 8 * * *`（每天 8:00 AM）
- 部署名称：`daily-morning-prediction`
- 标签：`production`, `daily`, `risk-prediction`

## 3. 时间旅行测试（回测模式）

### 3.1 使用 main.py 进行回测

对于特定日期的回测，继续使用原有的 `main.py`：

```bash
# 测试 2026-02-01 的预测能力
python main.py --as-of-date 2026-02-01 --companies 5

# 测试 2025-12-15 的预测能力
python main.py --as-of-date 2025-12-15 --companies 10
```

### 3.2 使用 Prefect 进行回测

修改 `prefect_pipeline.py` 的参数：

```python
# 临时修改 main 函数中的参数
result = credit_risk_pipeline(
    as_of_date="2026-02-01",  # 指定回测日期
    num_companies=5
)
```

然后运行：

```bash
python prefect_pipeline.py
```

## 4. Prefect 工作流详解

### 4.1 任务结构

Pipeline 包含 3 个主要任务：

```
credit_risk_pipeline (Flow)
│
├── select_companies_task
│   └── 使用 LLM 选择高风险公司
│       - 重试：3 次
│       - 延迟：60 秒
│
├── analyze_company_task (并发执行)
│   └── 分析每个公司的信用风险
│       - 并发执行（使用 .map()）
│       - 重试：3 次
│       - 延迟：60 秒
│
└── save_results_task
    └── 汇总结果并保存
        - 生成高风险公司列表
        - 保存到 JSON 文件
```

### 4.2 并发执行机制

```python
# 使用 .map() 实现并发分析
results = analyze_company_task.map(
    ticker=tickers,
    config=[config] * len(tickers),
    as_of_date=[as_of_date] * len(tickers)
)
```

**好处**：
- 多个公司并行分析，显著提升速度
- 自动处理失败重试
- Prefect 自动管理并发资源

### 4.3 错误处理

每个任务都配置了重试机制：

- **重试次数**：3 次
- **重试延迟**：60 秒
- **失败策略**：返回错误结果，不阻塞整个流程

## 5. 监控和可视化

### 5.1 查看 Prefect UI（可选）

如需可视化界面，启动 Prefect 服务器：

```bash
# 终端 1：启动 Prefect 服务器
prefect server start

# 终端 2：启动部署
python prefect_pipeline.py serve
```

访问 UI：
- URL: http://localhost:4200
- 查看任务执行历史
- 查看 DAG 图
- 监控任务状态

### 5.2 日志查看

所有日志都使用 Prefect 的 `get_run_logger()`，可以：

- 在终端查看实时日志
- 在 Prefect UI 查看历史日志
- 每个任务的日志独立记录

## 6. 生产部署建议

### 6.1 使用系统服务（Linux/macOS）

创建 systemd 服务文件 `/etc/systemd/system/credit-risk-pipeline.service`：

```ini
[Unit]
Description=Credit Risk Prediction Pipeline
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/pipeline-risk
Environment="PATH=/path/to/.venv/bin"
ExecStart=/path/to/.venv/bin/python prefect_pipeline.py serve
Restart=always

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable credit-risk-pipeline
sudo systemctl start credit-risk-pipeline
```

### 6.2 使用 Docker（推荐）

创建 `Dockerfile`：

```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY . /app

RUN pip install uv && uv sync

CMD ["python", "prefect_pipeline.py", "serve"]
```

运行：

```bash
docker build -t credit-risk-pipeline .
docker run -d --name risk-pipeline credit-risk-pipeline
```

### 6.3 使用云服务

- **Prefect Cloud**：托管调度和监控
- **AWS ECS/Lambda**：容器化部署
- **Google Cloud Run**：无服务器部署

## 7. 配置参数

### 7.1 修改调度时间

编辑 `prefect_pipeline.py`：

```python
credit_risk_pipeline.serve(
    name="daily-morning-prediction",
    cron="0 8 * * *",  # 修改这里
    ...
)
```

**常用 Cron 表达式**：
- `0 8 * * *`：每天早上 8:00
- `0 0 * * *`：每天午夜 12:00
- `0 9 * * 1-5`：工作日早上 9:00
- `0 */6 * * *`：每 6 小时一次

### 7.2 修改默认参数

编辑 `prefect_pipeline.py` 中的 `serve()` 参数：

```python
parameters={
    "as_of_date": None,      # None=实时模式，"YYYY-MM-DD"=回测模式
    "num_companies": 5       # 分析公司数量
}
```

## 8. 故障排查

### 8.1 Prefect 服务无法启动

```bash
# 检查 Prefect 是否安装
python -c "import prefect; print(prefect.__version__)"

# 重新安装
uv sync --force
```

### 8.2 任务失败

查看日志：

```bash
# 在终端查看
python prefect_pipeline.py

# 或在 Prefect UI 查看（如已启动）
```

常见问题：
- **API 配额超限**：等待配额重置（UTC 0:00）
- **网络错误**：检查网络连接和防火墙
- **公司验证失败**：检查 yfinance 是否可用

### 8.3 缓存问题

清除缓存：

```bash
rm -rf data/cache/*
```

## 9. 与原 main.py 的对比

| 特性 | main.py | prefect_pipeline.py |
|------|---------|---------------------|
| **用途** | 手动执行、回测 | 自动调度、生产环境 |
| **调度** | 无，需手动运行 | 支持 Cron 调度 |
| **并发** | 顺序执行 | 并发执行（.map()） |
| **监控** | 终端日志 | Prefect UI + 日志 |
| **重试** | 手动重试 | 自动重试 |
| **推荐场景** | 测试、调试、回测 | 日常生产运行 |

## 10. 快速命令参考

```bash
# 测试运行（单次）
python prefect_pipeline.py

# 生产部署（每天 8:00）
python prefect_pipeline.py serve

# 回测特定日期
python main.py --as-of-date 2026-02-01

# 启动 Prefect UI（可选）
prefect server start

# 清除缓存
rm -rf data/cache/*

# 查看依赖
uv pip list | grep prefect
```

## 11. 注意事项

1. **API 配额管理**
   - Gemini Free Tier：每天 ~20 次请求
   - 建议每天分析 5 个公司（默认配置）
   - 配额在 UTC 0:00（北京时间 8:00）重置

2. **时间约束**
   - 所有时间都基于系统本地时间
   - Cron 调度基于系统时区
   - 回测模式严格过滤 `as_of_date` 之后的数据

3. **数据持久化**
   - 结果保存在 `data/results/`
   - 缓存保存在 `data/cache/`（24 小时 TTL）
   - 建议定期备份结果文件

4. **安全性**
   - `.env` 文件包含 API 密钥，不要提交到 Git
   - 生产环境使用环境变量或密钥管理服务
   - 定期轮换 API 密钥
