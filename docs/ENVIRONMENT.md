# Environment Notes

本文档记录 Phase 1.5.1 的环境风险边界。当前阶段只固化 Mock MVP，不接真实行情、不接真实 LLM、不接 TradingAgents-astock、不接 a-stock-data、不接 use_cninfo。

## mootdx/httpx 风险

当前主环境存在 `mootdx/httpx` 版本约束风险：

```text
mootdx 0.11.7 requires httpx>=0.25.0,<0.26.0
current main environment uses httpx 0.28.1
```

Phase 1.5 Mock MVP 不依赖 mootdx。Mock Raw Data、Fact Pack、Scorecard、Decision、Risk Gate、Report、Paper Trading 和 SQLite Ledger 都不需要真实行情 Provider。

## 处理原则

- 不建议现在为了 mootdx 硬降级主环境 httpx。
- 后续接真实数据 Provider 前，应优先考虑 Provider 环境隔离、子进程隔离，或单独虚拟环境。
- 如果真实数据 Provider 需要 `mootdx`，应让 Provider 适配层输出统一的 `RawStockData`，不要让 Provider 依赖泄漏到后续 Fact Pack、Scorecard、Decision 链路。
- `python scripts/run_acceptance.py` 默认只做 core acceptance，不把 `pip check` 作为阻塞项。
- `python scripts/run_acceptance.py --strict-env` 会把 `pip check` 作为阻塞项，用于正式环境收敛前检查。

## 验收命令

```bash
python scripts/run_acceptance.py
```

默认命令只验证 private_ext Mock MVP 稳定性。

```bash
python scripts/run_acceptance.py --full-tests
```

运行全仓库测试。该命令用于观察 daily_stock_analysis 既有测试状态，不作为 Phase 1.5 默认阻塞项。

```bash
python scripts/run_acceptance.py --strict-env
```

运行严格环境检查。当前若仍存在 mootdx/httpx 冲突，该命令应失败并显示风险。
