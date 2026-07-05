from private_ext.fact_pack.models import StockFactPack
from private_ext.fact_pack.validators import is_missing, missing_keys
from private_ext.raw_data.models import RawStockData


class FactPackBuilder:
    def build(self, raw: RawStockData) -> StockFactPack:
        basic_info = raw.basic_info or {}
        market_snapshot = raw.market_snapshot or {}
        valuation_raw = raw.valuation_raw or {}
        financial_raw = raw.financial_raw or {}
        capital_flow_raw = raw.capital_flow_raw or {}
        northbound_raw = raw.northbound_raw or {}
        dragon_tiger_raw = raw.dragon_tiger_raw or {}
        announcements_raw = raw.announcements_raw or []
        news_raw = raw.news_raw or []
        industry_raw = raw.industry_raw or {}
        metadata = raw.metadata or {}
        quality_report = metadata.get("quality_report", {}) if isinstance(metadata.get("quality_report", {}), dict) else {}

        missing = []
        missing.extend(missing_keys(basic_info, ["name", "industry"], "basic_info"))
        missing.extend(missing_keys(market_snapshot, ["close"], "market_snapshot"))
        missing.extend(missing_keys(valuation_raw, ["pe", "pb"], "valuation_raw"))
        missing.extend(missing_keys(financial_raw, ["roe"], "financial_raw"))
        missing.extend(str(item) for item in metadata.get("missing_fields", []) if item)

        warnings = list(dict.fromkeys(str(item) for item in metadata.get("data_quality_warnings", []) if item))
        if not announcements_raw:
            warnings.append("announcement_evidence_missing")
        if not news_raw:
            warnings.append("news_evidence_missing")
        if len(missing) >= 3:
            warnings.append("core_fields_missing")
        if quality_report.get("quality_level") == "poor":
            warnings.append("数据质量较差，仅适合生成观察性报告，不适合强投资建议。")
        if quality_report.get("quality_level") == "failed":
            warnings.append("数据质量失败，评分和决策只能保守降级。")

        risk_facts = [{"risk": item, "severity": "medium"} for item in metadata.get("risk_events", []) if item]
        pe_value = valuation_raw.get("pe")
        if isinstance(pe_value, (int, float)) and pe_value >= 35:
            risk_facts.append({"risk": "高估值", "severity": "medium"})
        if missing:
            risk_facts.append({"risk": "部分真实数据缺失", "severity": "low"})

        growth_facts = {
            "revenue_growth": financial_raw.get("revenue_growth"),
            "profit_growth": financial_raw.get("profit_growth"),
            "net_profit_growth": financial_raw.get("net_profit_growth", financial_raw.get("profit_growth")),
            "industry_prosperity": industry_raw.get("prosperity"),
        }
        profitability_facts = {
            "roe": financial_raw.get("roe"),
            "gross_margin": financial_raw.get("gross_margin"),
            "net_margin": financial_raw.get("net_margin"),
        }
        balance_sheet_facts = {"debt_ratio": financial_raw.get("debt_ratio")}
        cashflow_facts = {
            "operating_cashflow_quality": financial_raw.get("operating_cashflow_quality"),
            "operating_cashflow": financial_raw.get("operating_cashflow"),
        }
        capital_flow_facts = {
            "main_net_inflow": capital_flow_raw.get("main_net_inflow"),
            "northbound_net_inflow": northbound_raw.get("net_inflow"),
            "dragon_tiger": dragon_tiger_raw,
            "super_large_net_inflow": capital_flow_raw.get("super_large_net_inflow"),
            "large_net_inflow": capital_flow_raw.get("large_net_inflow"),
            "mid_net_inflow": capital_flow_raw.get("mid_net_inflow"),
            "small_net_inflow": capital_flow_raw.get("small_net_inflow"),
        }

        if is_missing(market_snapshot.get("close")):
            warnings.append("close_price_missing")
        if is_missing(financial_raw.get("roe")):
            warnings.append("financial_roe_missing")

        return StockFactPack(
            symbol=raw.symbol,
            trade_date=raw.trade_date,
            identity={**basic_info},
            price_facts={**market_snapshot},
            valuation_facts={**valuation_raw},
            growth_facts=growth_facts,
            profitability_facts=profitability_facts,
            balance_sheet_facts=balance_sheet_facts,
            cashflow_facts=cashflow_facts,
            capital_flow_facts=capital_flow_facts,
            technical_facts={**(raw.kline_summary or {})},
            announcement_facts=announcements_raw,
            news_facts=news_raw,
            risk_facts=risk_facts,
            missing_fields=list(dict.fromkeys(missing)),
            data_quality_warnings=list(dict.fromkeys(warnings)),
            metadata={
                "provider": metadata.get("provider"),
                "requested_date": metadata.get("requested_date", raw.trade_date),
                "actual_data_date": metadata.get("actual_data_date"),
                "quality_level": quality_report.get("quality_level", "good"),
                "field_coverage_ratio": quality_report.get("field_coverage_ratio", 1.0),
                "can_score": quality_report.get("can_score", True),
                "can_make_decision": quality_report.get("can_make_decision", True),
                "failed_sources": quality_report.get("failed_sources", []),
                "successful_sources": quality_report.get("successful_sources", []),
                "field_provenance": metadata.get("field_provenance", {}),
                "source_cache_used": metadata.get("source_cache_used", []),
                "live_success_count": quality_report.get("live_success_count", 0),
                "cache_success_count": quality_report.get("cache_success_count", 0),
                "live_failure_count": quality_report.get("live_failure_count", 0),
                "critical_field_status": quality_report.get("critical_field_status", {}),
            },
        )
