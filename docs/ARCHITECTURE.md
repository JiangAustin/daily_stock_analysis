# ashare-research-os Architecture

本文档描述当前 Mock MVP 与 Phase 2 Real Data 的总体边界。目标是固化可重复、可回归的 A 股 AI 投研决策流水线；Phase 2 只接真实 Raw Data Provider，不接真实 LLM、不接 TradingAgents-astock、不开发前端。

## Pipeline

```text
Raw Data
  -> Fact Pack
  -> Scorecard
  -> Decision
  -> Risk Gate
  -> Report
  -> Paper Trading
  -> Evaluation
```

## 模块边界

- `scripts/run_stock_report.py`：唯一 MVP 验收入口，负责串联 Mock 原始数据、事实包、评分、决策、风控、报告、模拟交易和 SQLite 写入。
- `private_ext/raw_data/`：原始数据采集接口与实现，当前支持 `mock`，并新增 `akshare` 作为 Phase 2 真实 A 股 Raw Data Provider。
- `private_ext/raw_data/quality.py`：真实数据质量分级、覆盖率和可决策性判定。
- `private_ext/raw_data/cache.py`：Provider 级 `raw_cache` 与 source-level cache，用于缓存 `akshare` 原始快照并在 live 失败时回退。
- `private_ext/raw_data/akshare_fallbacks.py`：关键字段 fallback 和字段来源追踪。
- `private_ext/fact_pack/`：将 Raw Data 归一化为可评分的事实包。
- `private_ext/scoring/`：把 Fact Pack 转为 StockScorecard。
- `private_ext/research/`：研究适配器接口与 Mock 研究输出。当前不接真实 LLM。
- `private_ext/decisions/`：把 Scorecard 和研究输出转成 InvestmentDecision，并执行 Risk Gate。
- `private_ext/reports/`：生成结构化 Markdown 报告。
- `private_ext/paper_trading/`：执行模拟交易信号，不接实盘交易。
- `private_ext/database/`：SQLite schema、初始化和写入读取封装。
- `private_ext/evaluation/`：复盘评估占位，Phase 1.5 只保留接口边界。
- `scripts/inspect_db.py`：查看 SQLite Ledger 记录数量，辅助确认多次运行不会崩溃。
- `scripts/run_acceptance.py`：Phase 1.5 一键验收入口。
- `scripts/check_realdata_health.py`：只检查 Raw Data 和质量报告，不进入 Decision / Paper Trading。
- `scripts/check_realdata_health.py --verbose`：输出关键字段状态、字段来源、source cache 使用情况和 live/cache 成功失败统计。

## 验收分层

默认验收命令：

```bash
python scripts/run_acceptance.py
```

默认命令只运行 core acceptance，覆盖 private_ext Mock MVP 稳定性、Mock 报告生成、SQLite 检查、deterministic 输出检查、storage ignore 检查和文档存在检查。

全仓库测试命令：

```bash
python scripts/run_acceptance.py --full-tests
```

该命令会额外运行 `python -m pytest tests`，用于观察 daily_stock_analysis 既有全量测试状态，不作为 Phase 1.5 默认阻塞项。

严格环境检查命令：

```bash
python scripts/run_acceptance.py --strict-env
```

该命令会把 `python -m pip check` 失败作为阻塞项。当前主环境存在 `mootdx/httpx` 版本约束风险，详见 `docs/ENVIRONMENT.md`。

## 数据落盘

- `storage/raw/`：Mock Raw Data JSON。
- `storage/raw_cache/`：Provider 原始数据缓存，不替代每次 run 的 `storage/raw/` 快照。
- `storage/fact_packs/`：StockFactPack JSON。
- `storage/scorecards/`：StockScorecard JSON。
- `storage/reports/`：结构化 Markdown 报告。
- `storage/logs/`：运行日志。
- `storage/research.sqlite`：研究流水线 SQLite Ledger。

上述文件均属于运行产物，默认不入库；目录通过 `.gitkeep` 保留。

## 稳定性规则

- 同一股票、同一日期、同一 Mock 配置应生成稳定的 Raw Data、Fact Pack、Scorecard 和 Report 文件。
- 同一天重复运行允许在 SQLite 中追加 run 记录，但不得崩溃；`scripts/inspect_db.py` 必须能清楚显示 Ledger 记录数量。
- 报告文件采用固定文件名，重复运行会覆盖同名 Markdown 报告，避免不可控报告堆积。
- 当前阶段不改变 daily_stock_analysis 原 Web / Desktop 逻辑。
- 真实数据链路需要区分 `requested_date` 与 `actual_data_date`，不能假设第三方接口一定返回请求日数据。
- 关键字段必须记录 provenance，报告中需要明确哪些字段来自 live source、source cache 或 final raw cache。
- 单个 source 失败不应直接拖垮整只股票；优先走 source-level cache 和字段级 fallback，再由质量报告决定是否允许决策。

## 后续阶段边界

- Phase 2 接单一真实 A 股数据 Provider，但仍输出 RawStockData 并复用后续链路；默认验收仍以 Mock acceptance 为准，真实数据只通过独立 smoke 验证。
- Phase 2.1 增加 Raw Data Quality Report、缓存回退和 health check，但仍不接真实 LLM、公告证据或多 Agent。
- Phase 3 才接公告证据链。
- Phase 4 才接 TradingAgents-astock，并只用于重点股票深度分析。
