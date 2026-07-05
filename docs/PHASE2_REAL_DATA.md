# Phase 2 Real Data Provider

Phase 2 只接真实 Raw Data，不接真实 LLM。

默认验收仍以 mock acceptance 为准。

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

已知风险：

- 网络不稳定
- 数据源字段变化
- akshare 函数版本差异
- mootdx/httpx 依赖冲突仍不应影响 Mock MVP

失败处理：

- 字段缺失进入 `missing_fields`
- 数据异常进入 `data_quality_warnings`
- 单只股票失败不影响其他股票

下一阶段：

- `use_cninfo` 公告证据
- `TradingAgents-astock` 深度研究
- Evaluation 复盘
