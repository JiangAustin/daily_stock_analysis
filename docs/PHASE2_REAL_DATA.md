# Phase 2 Real Data Provider

Phase 2 只接真实 Raw Data，不接真实 LLM。

默认验收仍以 mock acceptance 为准。

新增 `RawDataQualityReport`，用于描述：

- `requested_date`：用户请求日期
- `actual_data_date`：数据源实际返回日期，可能与请求日期不同
- `quality_level`：`good / degraded / poor / failed`
- `field_coverage_ratio`
- `can_score`
- `can_make_decision`

新增 `raw_cache` 机制：

- Provider 缓存在 `storage/raw_cache/{provider}/`
- 默认真实数据 smoke 优先使用缓存，降低 live network 抖动
- `--refresh-data` 会强制 live 拉取并覆盖缓存
- live 失败且缓存存在时会回退缓存，并记录 `used_stale_cache_due_to_live_failure`

`akshare` provider 安装方式：

```bash
pip install -r requirements-realdata.txt
```

真实数据 smoke 命令：

```bash
python scripts/run_realdata_smoke.py
```

手动命令：

```bash
python scripts/run_stock_report.py --stocks 600519 --date 2026-07-03 --raw-data akshare --research-adapter mock --paper-trading off
```

真实数据健康检查：

```bash
python scripts/check_realdata_health.py --stocks 600519,000001,300750 --raw-data akshare
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

为什么真实数据 smoke 不是默认 acceptance 的一部分：

- 真实数据依赖外部网络和第三方接口稳定性
- `akshare` 字段可能随版本和上游接口变化
- Phase 1.5 默认 acceptance 需要保持 deterministic
- Mock MVP 仍是当前主阻塞项，真实数据用独立 smoke 和 health check 观测

下一阶段：

- `use_cninfo` 公告证据
- `TradingAgents-astock` 深度研究
- Evaluation 复盘
