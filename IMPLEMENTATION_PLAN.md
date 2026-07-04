# A股 AI 投研决策流水线最终实施计划

## 0. 项目目标

本项目目标是构建一个稳定、可扩展、可审计、可复盘的 A股 AI 投研决策流水线。

核心链路：

```text
Raw Data
  ↓
Fact Pack
  ↓
Scorecard
  ↓
Investment Decision
  ↓
Risk Gate
  ↓
Structured Report
  ↓
Paper Trading
  ↓
Review / Evaluation
```

第一阶段目标不是追求真实数据和真实 LLM，而是先跑通 Mock 闭环。

## 1. 总体设计

### 1.1 为什么不是直接让 LLM 分析？

本项目禁止跳过 Fact Pack 和 Scorecard 直接让 LLM 给出买卖建议。

正确流程是：

```text
原始数据先结构化
结构化数据再形成 Fact Pack
Fact Pack 再生成分项评分
评分和事实一起进入 Decision Engine
Decision 经过 Risk Gate
最终才进入报告和模拟交易
```

原因：

1. 提高稳定性
2. 降低幻觉
3. 方便复盘
4. 方便替换数据源和模型
5. 方便验证评分和决策是否有效

## 2. 第一阶段 MVP

### 2.1 MVP 验收命令

Phase 1.5 以后默认验收命令为：

```bash
python scripts/run_acceptance.py
```

默认命令只执行 core acceptance，不运行全仓库测试，不把严格环境检查作为阻塞项。

可选全仓库测试：

```bash
python scripts/run_acceptance.py --full-tests
```

该命令会额外执行 `python -m pytest tests`，用于观察既有 daily_stock_analysis 测试状态，不作为 Phase 1.5 默认阻塞项。

可选严格环境检查：

```bash
python scripts/run_acceptance.py --strict-env
```

该命令会把 `python -m pip check` 失败作为阻塞项。当前 `mootdx/httpx` 版本约束风险详见 `docs/ENVIRONMENT.md`。

原始 Mock MVP 命令仍可单独运行：

```bash
python scripts/run_stock_report.py \
  --stocks 600519,000001,300750 \
  --date 2026-07-03 \
  --raw-data mock \
  --research-adapter mock \
  --paper-trading on
```

### 2.2 MVP 输出文件

必须生成：

```text
storage/research.sqlite

storage/fact_packs/600519_2026-07-03.json
storage/fact_packs/000001_2026-07-03.json
storage/fact_packs/300750_2026-07-03.json

storage/scorecards/600519_2026-07-03.json
storage/scorecards/000001_2026-07-03.json
storage/scorecards/300750_2026-07-03.json

storage/reports/stock_report_600519_2026-07-03.md
storage/reports/stock_report_000001_2026-07-03.md
storage/reports/stock_report_300750_2026-07-03.md

storage/logs/run_stock_report_2026-07-03.log
```

### 2.3 MVP 数据库要求

SQLite 至少包含：

```text
research_runs
raw_data_snapshots
fact_packs
scorecards
research_decisions
paper_trade_signals
paper_orders
paper_positions
paper_nav
```

## 3. 目录结构

第一阶段必须实现 `private_ext/` 扩展层、`scripts/run_stock_report.py`、`scripts/inspect_db.py` 和对应测试。`daily_stock_analysis` 原有代码只作为稳定外壳，MVP 不改 Web、桌面端、真实行情、真实 LLM、推送或实盘交易。

## 4. Phase 0/1 验收清单

```text
[ ] AGENTS.md 存在
[ ] IMPLEMENTATION_PLAN.md 存在
[ ] private_ext 目录存在
[ ] scripts/run_stock_report.py 存在
[ ] scripts/inspect_db.py 存在
[ ] python scripts/run_acceptance.py 成功
[ ] python scripts/run_acceptance.py --full-tests 可用于观察全仓库测试
[ ] python scripts/run_acceptance.py --strict-env 可用于严格环境检查
[ ] Mock MVP 命令成功
[ ] storage/research.sqlite 存在
[ ] storage/fact_packs 至少 3 个 JSON
[ ] storage/scorecards 至少 3 个 JSON
[ ] storage/reports 至少 3 个 Markdown 报告
[ ] SQLite 中 research_runs 至少 3 条
[ ] SQLite 中 fact_packs 至少 3 条
[ ] SQLite 中 scorecards 至少 3 条
[ ] SQLite 中 research_decisions 至少 3 条
[ ] SQLite 中 paper_nav 至少 1 条
[ ] 没有新增前端
[ ] 没有接入实盘
[ ] 没有破坏 daily_stock_analysis 原有结构
```
