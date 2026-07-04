from private_ext.fact_pack.models import StockFactPack
from private_ext.fact_pack.validators import missing_keys
from private_ext.raw_data.models import RawStockData


class FactPackBuilder:
    def build(self, raw: RawStockData) -> StockFactPack:
        missing = []
        missing.extend(missing_keys(raw.basic_info, ["name", "industry"], "basic_info"))
        missing.extend(missing_keys(raw.market_snapshot, ["close"], "market_snapshot"))
        missing.extend(missing_keys(raw.valuation_raw, ["pe", "pb"], "valuation_raw"))

        warnings = []
        if not raw.announcements_raw:
            warnings.append("announcement_evidence_missing")
        if len(missing) >= 3:
            warnings.append("core_fields_missing")

        risk_facts = [{"risk": item, "severity": "medium"} for item in raw.metadata.get("risk_events", [])]
        if raw.valuation_raw.get("pe", 0) >= 35:
            risk_facts.append({"risk": "高估值", "severity": "medium"})

        return StockFactPack(
            symbol=raw.symbol,
            trade_date=raw.trade_date,
            identity={**raw.basic_info},
            price_facts={**raw.market_snapshot},
            valuation_facts={**raw.valuation_raw},
            growth_facts={
                "revenue_growth": raw.financial_raw.get("revenue_growth"),
                "profit_growth": raw.financial_raw.get("profit_growth"),
                "industry_prosperity": raw.industry_raw.get("prosperity"),
            },
            profitability_facts={
                "roe": raw.financial_raw.get("roe"),
                "gross_margin": raw.financial_raw.get("gross_margin"),
                "net_margin": raw.financial_raw.get("net_margin"),
            },
            balance_sheet_facts={"debt_ratio": raw.financial_raw.get("debt_ratio")},
            cashflow_facts={"operating_cashflow_quality": raw.financial_raw.get("operating_cashflow_quality")},
            capital_flow_facts={
                "main_net_inflow": raw.capital_flow_raw.get("main_net_inflow"),
                "northbound_net_inflow": raw.northbound_raw.get("net_inflow"),
                "dragon_tiger": raw.dragon_tiger_raw,
            },
            technical_facts={**raw.kline_summary},
            announcement_facts=raw.announcements_raw,
            news_facts=raw.news_raw,
            risk_facts=risk_facts,
            missing_fields=missing,
            data_quality_warnings=warnings,
        )

