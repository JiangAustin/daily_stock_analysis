from pathlib import Path

from private_ext.decisions.models import InvestmentDecision
from private_ext.fact_pack.models import StockFactPack
from private_ext.paper_trading.models import PaperTradeExecution
from private_ext.reports.markdown_renderer import bullet_list
from private_ext.scoring.models import StockScorecard


DISCLAIMER = "本报告由 AI 辅助生成，仅用于个人研究和模拟交易，不构成投资建议。市场有风险，投资需谨慎。"
PROVENANCE_FIELDS = [
    "market_snapshot.close",
    "market_snapshot.pct_change",
    "kline_summary.return_5d",
    "kline_summary.return_20d",
    "kline_summary.return_60d",
    "valuation_raw.pe",
    "valuation_raw.pb",
    "financial_raw.roe",
    "financial_raw.net_profit_growth",
]


def render_stock_report(
    fact_pack: StockFactPack,
    scorecard: StockScorecard,
    decision: InvestmentDecision,
    execution: PaperTradeExecution,
    reports_dir: Path,
) -> Path:
    reports_dir.mkdir(parents=True, exist_ok=True)
    name = fact_pack.identity.get("name", fact_pack.symbol)
    quality = fact_pack.metadata or {}
    field_provenance = quality.get("field_provenance", {}) or {}
    degraded_notice = ""
    if quality.get("quality_level", "good") != "good":
        degraded_notice = "\n> 当前报告基于降级数据生成，结论仅供观察，不应作为强交易依据。\n"
    source_cache_notice = ""
    if quality.get("source_cache_used"):
        source_cache_notice = "\n> 本报告部分字段使用本地缓存数据，可能不是最新实时数据。\n"
    actual_date_notice = ""
    requested_date = quality.get("requested_date", fact_pack.trade_date)
    actual_date = quality.get("actual_data_date")
    if actual_date not in (None, "", "None") and requested_date and actual_date != requested_date:
        actual_date_notice = (
            f"\n> 本报告使用的数据实际日期为 {actual_date}，与请求日期 {requested_date} 不完全一致。\n"
        )
    content = f"""# A股AI投研报告 - {name}({fact_pack.symbol})

> {DISCLAIMER}
{degraded_notice}
{source_cache_notice}
{actual_date_notice}

## 1. 结论摘要

| 项目 | 结果 |
|---|---|
| 综合评分 | {scorecard.total_score} |
| 投资评级 | {decision.rating} |
| 建议动作 | {decision.action} |
| 置信度 | {decision.confidence:.2f} |
| 建议仓位 | {decision.target_position:.2%} |
| 投资周期 | {decision.horizon} |

## 运行信息

| 项目 | 值 |
|---|---|
| Run Mode | {quality.get("run_mode", "-")} |
| Raw Data Provider | {quality.get("provider", "unknown")} |
| Research Adapter | {quality.get("research_adapter", "-")} |
| Run ID | {quality.get("file_run_id", "-")} |
| Run Directory | {quality.get("run_dir", "-")} |

## 数据质量与可用性

| 项目 | 结果 |
|---|---|
| 数据源 | {quality.get("provider", "unknown")} |
| 请求日期 | {quality.get("requested_date", fact_pack.trade_date)} |
| 实际数据日期 | {quality.get("actual_data_date", "None")} |
| 数据质量等级 | {quality.get("quality_level", "good")} |
| 字段覆盖率 | {quality.get("field_coverage_ratio", 1.0)} |
| 是否可评分 | {quality.get("can_score", True)} |
| 是否可形成投资决策 | {quality.get("can_make_decision", True)} |
| Providers Used | {", ".join(quality.get("providers_used", [])) or quality.get("provider", "unknown")} |
| Merge Warnings | {", ".join(quality.get("merge_warnings", [])) or "-"} |

### 缺失字段
{bullet_list(fact_pack.missing_fields)}

### 数据源警告
{bullet_list(fact_pack.data_quality_warnings)}

### 失败数据源
{bullet_list(quality.get("failed_sources", []))}

### 数据源成功/失败统计

| 项目 | 数量 |
|---|---:|
| Live 成功源 | {quality.get("live_success_count", 0)} |
| Cache 成功源 | {quality.get("cache_success_count", 0)} |
| Live 失败源 | {quality.get("live_failure_count", 0)} |

### 关键字段来源
{_render_provenance_table(field_provenance)}

{_render_eastmoney_diagnostics(quality)}

## 2. Fact Pack 核心事实

### 2.1 基础信息
{bullet_list([f"{key}: {value}" for key, value in fact_pack.identity.items()])}

### 2.2 行情与技术事实
{bullet_list([f"{key}: {value}" for key, value in {**fact_pack.price_facts, **fact_pack.technical_facts}.items()])}

### 2.3 估值事实
{bullet_list([f"{key}: {value}" for key, value in fact_pack.valuation_facts.items()])}

### 2.4 盈利与成长事实
{bullet_list([f"{key}: {value}" for key, value in {**fact_pack.profitability_facts, **fact_pack.growth_facts}.items()])}

### 2.5 资金面事实
{bullet_list([f"{key}: {value}" for key, value in fact_pack.capital_flow_facts.items()])}

### 2.6 公告与新闻事实
{bullet_list([item.get("title", "") for item in [*fact_pack.announcement_facts, *fact_pack.news_facts]])}

### 2.7 风险事实
{bullet_list([item.get("risk", "") for item in fact_pack.risk_facts])}

### 2.8 数据缺失与质量警告
{bullet_list([*fact_pack.missing_fields, *fact_pack.data_quality_warnings])}

## 3. 分项评分

| 维度 | 分数 | 解释 |
|---|---:|---|
| 估值 | {scorecard.valuation_score} | {scorecard.score_explanations["valuation"]} |
| 成长 | {scorecard.growth_score} | {scorecard.score_explanations["growth"]} |
| 盈利 | {scorecard.profitability_score} | {scorecard.score_explanations["profitability"]} |
| 财务健康 | {scorecard.financial_health_score} | {scorecard.score_explanations["financial_health"]} |
| 资金面 | {scorecard.capital_flow_score} | {scorecard.score_explanations["capital_flow"]} |
| 技术面 | {scorecard.technical_score} | {scorecard.score_explanations["technical"]} |
| 情绪面 | {scorecard.sentiment_score} | {scorecard.score_explanations["sentiment"]} |
| 风险 | {scorecard.risk_score} | {scorecard.score_explanations["risk"]} |

## 4. 投资逻辑

### 看多理由
{bullet_list(decision.bullish_points)}

### 看空理由
{bullet_list(decision.bearish_points)}

### 关键催化
{bullet_list(decision.catalysts)}

### 主要风险
{bullet_list(decision.risks)}

### 失效条件
{bullet_list(decision.invalidation_conditions)}

## 5. 操作建议

### 激进方案
{decision.aggressive_plan}

### 稳健方案
{decision.balanced_plan}

### 保守方案
{decision.conservative_plan}

## 6. 模拟交易执行

| 动作 | 价格 | 数量 | 金额 | 费用 | 是否执行 | 原因 |
|---|---:|---:|---:|---:|---|---|
| {execution.action} | {execution.price:.2f} | {execution.quantity} | {execution.amount:.2f} | {execution.fee:.2f} | {"是" if execution.executed else "否"} | {execution.reason} |

## 7. 模拟交易执行复核

- Risk Gate 结果：{decision.risk_gate_reason}
- 模拟交易动作：{execution.action}

## 8. 后续复盘计划

- T+1 检查：价格、资金流和公告是否验证原始判断。
- T+5 检查：评分变化和风险事件是否触发失效条件。
- T+20 检查：投资逻辑是否仍成立。
- 需要跟踪的事件：{", ".join(decision.catalysts)}

## 9. 风险提示

{DISCLAIMER}
"""
    path = reports_dir / f"stock_report_{fact_pack.symbol}_{fact_pack.trade_date}.md"
    path.write_text(content, encoding="utf-8")
    return path


def _render_provenance_table(field_provenance: dict[str, dict[str, object]]) -> str:
    lines = [
        "| 字段 | 值是否存在 | 来源 | Fallback等级 | 是否缓存 | 置信度 |",
        "|---|---|---|---:|---|---|",
    ]
    for field in PROVENANCE_FIELDS:
        payload = field_provenance.get(field, {}) or {}
        source = payload.get("source", "-") or "-"
        confidence = payload.get("confidence", "-") or "-"
        exists = "是" if source != "-" and confidence != "missing" else "否"
        lines.append(
            "| {field} | {exists} | {source} | {fallback_level} | {cached} | {confidence} |".format(
                field=field,
                exists=exists,
                source=source,
                fallback_level=payload.get("fallback_level", "-"),
                cached="yes" if payload.get("is_cached") else "no",
                confidence=confidence,
            )
        )
    return "\n".join(lines)


def _render_eastmoney_diagnostics(quality: dict[str, object]) -> str:
    diagnostics = (
        quality.get("eastmoney_diagnostics")
        or quality.get("diagnostics")
        or quality.get("provider_reports", {}).get("eastmoney", {}).get("diagnostics", {})
    )
    endpoint_results = diagnostics.get("endpoint_results", []) if isinstance(diagnostics, dict) else []
    if not endpoint_results:
        return ""
    lines = [
        "### EastMoney Endpoint 诊断",
        "",
        "| Endpoint | 状态 | 命中字段 | 缺失字段 | 错误类型 | 是否缓存 |",
        "|---|---|---|---|---|---|",
    ]
    for item in endpoint_results:
        lines.append(
            "| {endpoint} | {status} | {found} | {missing} | {error_type} | {cached} |".format(
                endpoint=item.get("endpoint_name", "-"),
                status=item.get("status", "-"),
                found=", ".join(item.get("fields_found", [])) or "-",
                missing=", ".join(item.get("fields_missing", [])) or "-",
                error_type=item.get("error_type") or "-",
                cached="yes" if item.get("used_cache") else "no",
            )
        )
    candidate_results = diagnostics.get("candidate_results", []) if isinstance(diagnostics, dict) else []
    if candidate_results:
        lines.extend(
            [
                "",
                "#### Candidate 级详情",
                "",
                "| Group | Candidate | 状态 | 命中字段 | 缺失字段 | 错误类型 | 是否缓存 |",
                "|---|---|---|---|---|---|---|",
            ]
        )
        counts: dict[str, int] = {}
        for item in candidate_results:
            group = item.get("endpoint_group", "-")
            counts[group] = counts.get(group, 0) + 1
            if counts[group] > 3:
                continue
            lines.append(
                "| {group} | {candidate} | {status} | {found} | {missing} | {error_type} | {cached} |".format(
                    group=group,
                    candidate=item.get("candidate_name", "-"),
                    status=item.get("status", "-"),
                    found=", ".join(item.get("fields_found", [])) or "-",
                    missing=", ".join(item.get("fields_missing", [])) or "-",
                    error_type=item.get("error_type") or "-",
                    cached="yes" if item.get("used_cache") else "no",
                )
            )
        lines.append("")
        lines.append("> 完整 candidate 结果见 RawStockData metadata。")
    return "\n".join(lines)
