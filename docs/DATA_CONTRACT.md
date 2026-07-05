# Data Contract

本文档记录 Phase 1.5 Mock MVP 的核心数据契约。字段契约以 `private_ext/` 中的 Pydantic model 为准，本文档用于协作和验收说明。

## RawStockData

来源：`private_ext/raw_data/models.py`

用途：表示原始股票数据快照。Phase 1.5 由 Mock collector 生成；Phase 2 开始真实数据 Provider 也必须先适配成该结构，不能绕过 Fact Pack。

字段：

- `symbol: str`：股票代码，例如 `600519`。
- `trade_date: str`：交易日期，格式为 `YYYY-MM-DD`。
- `basic_info: dict`：公司基础信息，如名称、行业、市场。
- `market_snapshot: dict`：收盘价、币种、涨跌幅等行情快照。
- `kline_summary: dict`：趋势、均线、波动率等 K 线摘要。
- `valuation_raw: dict`：PE、PB、股息率等原始估值数据。
- `financial_raw: dict`：ROE、毛利率、净利率、营收增长、利润增长等财务数据。
- `capital_flow_raw: dict`：主力净流入等资金面数据。
- `northbound_raw: dict`：北向资金数据。
- `dragon_tiger_raw: dict`：龙虎榜数据。
- `announcements_raw: list[dict]`：公告摘要列表。
- `news_raw: list[dict]`：新闻摘要列表。
- `analyst_raw: list[dict]`：分析师观点列表。
- `industry_raw: dict`：行业景气与行业上下文。
- `metadata: dict`：数据源、生成方式、质量标记等元数据。

稳定性要求：

- Mock 输出必须 deterministic。
- 真实 Provider 只能替换 Raw Data 来源，不应改变下游字段语义。
- RawStockData 的各字段允许部分为空；真实 Provider 应尽量填充，但缺失字段不得导致 collector 绕过该契约或直接让下游崩溃。
- 真实 Provider 应把抓取失败、字段漂移和降级信息写入 `metadata`，由后续 FactPackBuilder 继续转换成 `missing_fields` / `data_quality_warnings`。

## StockFactPack

来源：`private_ext/fact_pack/models.py`

用途：把 RawStockData 清洗为下游评分和报告可直接消费的事实集合。

字段：

- `symbol: str`：股票代码。
- `trade_date: str`：交易日期。
- `identity: dict`：公司身份信息。
- `price_facts: dict`：价格与行情事实。
- `valuation_facts: dict`：估值事实。
- `growth_facts: dict`：成长性事实。
- `profitability_facts: dict`：盈利质量事实。
- `balance_sheet_facts: dict`：资产负债事实。
- `cashflow_facts: dict`：现金流事实。
- `capital_flow_facts: dict`：资金面事实。
- `technical_facts: dict`：技术面事实。
- `announcement_facts: list[dict]`：公告事实。
- `news_facts: list[dict]`：新闻事实。
- `risk_facts: list[dict]`：风险事实。
- `missing_fields: list[str]`：缺失字段列表。
- `data_quality_warnings: list[str]`：数据质量警告。

稳定性要求：

- Fact Pack 只做归一化和事实抽取，不直接给投资建议。
- 缺失数据应进入 `missing_fields` 或 `data_quality_warnings`，不要静默吞掉。
- FactPackBuilder 必须兼容真实数据 Provider 的部分缺失、空 dict、空 list 和 `None` 风险输入。

## StockScorecard

来源：`private_ext/scoring/models.py`

用途：将 StockFactPack 转为可解释分项评分和总评分。

字段：

- `symbol: str`：股票代码。
- `trade_date: str`：交易日期。
- `valuation_score: float`：估值评分。
- `growth_score: float`：成长评分。
- `profitability_score: float`：盈利评分。
- `financial_health_score: float`：财务健康评分。
- `capital_flow_score: float`：资金面评分。
- `technical_score: float`：技术面评分。
- `sentiment_score: float`：情绪评分。
- `risk_score: float`：风险评分。
- `total_score: float`：综合评分。
- `rating_band: str`：评分分层，例如 `neutral-bullish`。
- `score_explanations: dict[str, str]`：每个维度的解释。
- `penalty_reasons: list[str]`：扣分原因。

稳定性要求：

- 同一 Fact Pack 必须生成同一 Scorecard。
- 评分解释必须能对应到事实字段，避免黑箱分数。
- ScoreEngine 必须能处理缺失字段；字段不足时给中性或保守分，并把保守处理写进 `score_explanations` 与 `penalty_reasons`。

## InvestmentDecision

来源：`private_ext/decisions/models.py`

用途：表达研究结论、动作建议、仓位建议、风控结果和可复盘条件。

字段：

- `symbol: str`：股票代码。
- `trade_date: str`：交易日期。
- `rating: str`：投资评级。
- `action: str`：建议动作，例如 `watch`、`buy`、`sell`、`hold`。
- `confidence: float`：置信度，范围应控制在 0 到 1。
- `target_position: float`：建议目标仓位。
- `horizon: str`：投资周期。
- `thesis: str`：核心投资逻辑。
- `bullish_points: list[str]`：看多理由。
- `bearish_points: list[str]`：看空理由。
- `catalysts: list[str]`：关键催化。
- `risks: list[str]`：主要风险。
- `invalidation_conditions: list[str]`：失效条件。
- `aggressive_plan: str`：激进方案。
- `balanced_plan: str`：稳健方案。
- `conservative_plan: str`：保守方案。
- `risk_gate_passed: bool`：Risk Gate 是否通过。
- `risk_gate_reason: str | None`：Risk Gate 拦截或通过原因。

稳定性要求：

- InvestmentDecision 不能绕过 Risk Gate 进入模拟交易。
- 当前阶段只允许 Mock research adapter 生成研究输出，不调用真实 LLM。
- 模拟交易结果必须记录为 Paper Trading，不产生真实交易行为。
