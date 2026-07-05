# Phase 2 Real Data Provider

Phase 2 只接真实 Raw Data，不接真实 LLM。

Phase 2.4 新增第二 Provider `eastmoney`，并通过 `composite` 做字段级合并：

```text
akshare
  +
eastmoney
  ->
CompositeRawDataCollector
  ->
RawStockData
```

默认验收仍以 mock acceptance 为准。

运行产物隔离：

- 每次执行 `run_stock_report.py` 都会生成独立 `file_run_id`
- 产物默认写入 `storage/runs/{file_run_id}/...`
- 最新指针按 run mode 隔离：
  - `storage/latest_mock_mvp/`
  - `storage/latest_realdata_smoke/`
  - `storage/latest_manual/`
- mock acceptance 与 realdata smoke 不再共用同一路径

新增 `RawDataQualityReport`，用于描述：

- `requested_date`：用户请求日期
- `actual_data_date`：数据源实际返回日期，可能与请求日期不同
- `quality_level`：`good / degraded / poor / failed`
- `field_coverage_ratio`
- `can_score`
- `can_make_decision`
- `critical_field_status`
- `field_provenance_summary`
- `source_cache_used`
- `live_success_count / cache_success_count / live_failure_count`

新增 `raw_cache` 机制：

- Provider 缓存在 `storage/raw_cache/{provider}/`
- Source-level cache 缓存在 `storage/raw_cache/{provider}/source/{source_name}/`
- 默认真实数据 smoke 优先使用缓存，降低 live network 抖动
- `--refresh-data` 会强制 live 拉取，并禁止 final raw cache 与 source-level cache 回退
- 默认模式下 live 失败且缓存存在时会回退缓存，并记录 `used_stale_cache_due_to_live_failure`
- 单个 source live 失败时，会优先尝试 source-level cache，并在 provenance 中标记 `is_cached=true`

K 线专项回补：

- `private_ext/raw_data/akshare_kline.py` 负责 A 股 symbol 标准化、K 线 fallback、close/pct_change 提取和 `return_5d/20d/60d` 计算
- `requested_date` 与 `actual_data_date` 不一定一致
- 当数据源只能返回最新可用交易日时，报告和质量报告都要显示 `actual_data_date`
- `close`、`pct_change`、`return_20d` 是行情核心字段
- `return_20d` 优先来自 hist K 线计算；source cache 和 final raw cache 只作为回退
- 如果 K 线窗口不足，允许保留 `return_20d=None` 并写入 `insufficient_kline_window_for_return_20d`

`akshare` provider 安装方式：

```bash
pip install -r requirements-realdata.txt
```

真实数据 smoke 命令：

```bash
python scripts/run_realdata_smoke.py
```

组合 provider smoke：

```bash
python scripts/run_realdata_smoke.py --raw-data composite
```

手动命令：

```bash
python scripts/run_stock_report.py --stocks 600519 --date 2026-07-03 --raw-data akshare --research-adapter mock --paper-trading off
```

真实数据健康检查：

```bash
python scripts/check_realdata_health.py --stocks 600519,000001,300750 --raw-data akshare
```

详细健康检查：

```bash
python scripts/check_realdata_health.py --stocks 600519,000001,300750 --raw-data akshare --verbose
```

组合 provider 健康检查：

```bash
python scripts/check_realdata_health.py --stocks 600519,000001,300750 --raw-data composite --verbose
```

强制实时刷新：

```bash
python scripts/check_realdata_health.py --stocks 600519,000001,300750 --raw-data akshare --refresh-data --verbose
```

已知风险：

- 网络不稳定
- 数据源字段变化
- akshare 函数版本差异
- mootdx/httpx 依赖冲突仍不应影响 Mock MVP

失败处理：

- 字段缺失进入 `missing_fields`
- 数据异常进入 `data_quality_warnings`
- 单只股票失败不影响其他股票
- `degraded` 数据会限制 Scorecard 总分上限
- `poor` 数据不允许强 `buy`
- `failed` 数据不应生成强决策
- 非核心字段如新闻、公告、部分资金流缺失，不应单独把质量直接打到 `poor`
- `PE/PB` 缺失不再直接决定整体 `poor`；只在估值维度保守处理

关键字段来源说明：

- 报告会输出 `关键字段来源` 表，展示关键字段来自 live source、source cache 还是 final raw cache
- 当前重点跟踪：`close`、`pct_change`、`pe`、`pb`、`roe`、`net_profit_growth`、`return_20d`
- `composite` 模式下还会输出 `Providers Used` 和 `Merge Warnings`
- `eastmoney` provider 会记录 endpoint 级 diagnostics，展示每个 endpoint 的状态、命中字段、错误类型、是否使用 source cache 和耗时
- Phase 2.4.2 新增 candidate 机制：每个 endpoint group 可以有多个 candidate，按 priority 顺序尝试，记录 candidate 级状态、URL/参数摘要、解析结果和 cache 使用情况

EastMoney endpoint probe：

```bash
python scripts/probe_eastmoney_endpoints.py --stocks 600519,000001,300750
python scripts/probe_eastmoney_endpoints.py --stocks 600519 --group kline --refresh-data --print-json
```

为什么 probe 不属于 acceptance：

- probe 直接依赖 EastMoney live network
- 目标是诊断 candidate 连通性，不是验证 Mock MVP 稳定性
- 即使 probe 全部失败，也不应阻塞默认 mock acceptance

为什么真实数据 smoke 不是默认 acceptance 的一部分：

- 真实数据依赖外部网络和第三方接口稳定性
- `akshare` 字段可能随版本和上游接口变化
- Phase 1.5 默认 acceptance 需要保持 deterministic
- Mock MVP 仍是当前主阻塞项，真实数据用独立 smoke 和 health check 观测

下一阶段：

- `use_cninfo` 公告证据
- `TradingAgents-astock` 深度研究
- Evaluation 复盘
