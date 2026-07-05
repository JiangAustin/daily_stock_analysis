from __future__ import annotations

from private_ext.raw_data.akshare_collector import AkShareRawDataCollector
from private_ext.raw_data.base import RawDataCollector
from private_ext.raw_data.eastmoney_diagnostics import EastMoneyDiagnosticsReport
from private_ext.raw_data.eastmoney_collector import EastMoneyRawDataCollector
from private_ext.raw_data.merge import merge_raw_stock_data
from private_ext.raw_data.quality import build_quality_report


class CompositeRawDataCollector(RawDataCollector):
    provider = "composite"

    def __init__(self, primary: RawDataCollector | None = None, secondary: RawDataCollector | None = None, **kwargs):
        self.primary = primary or AkShareRawDataCollector(**kwargs)
        self.secondary = secondary or EastMoneyRawDataCollector(**kwargs)

    def collect(self, symbol: str, trade_date: str):
        primary_raw = self.primary.collect(symbol, trade_date)
        secondary_raw = self.secondary.collect(symbol, trade_date)
        merged = merge_raw_stock_data(primary_raw, secondary_raw)
        merged.metadata["provider"] = self.provider
        merged.metadata["providers_used"] = ["akshare", "eastmoney"]
        eastmoney_diagnostics = secondary_raw.metadata.get("eastmoney_diagnostics") or EastMoneyDiagnosticsReport(
            symbol=secondary_raw.symbol,
            requested_date=trade_date,
            endpoint_results=[],
            successful_endpoints=[],
            failed_endpoints=[],
            fields_filled_by_endpoint={},
            unresolved_fields=[],
            remote_errors=[],
            cache_used=[],
            notes=[],
        ).model_dump(mode="json")
        merged.metadata["provider_reports"] = {
            "akshare": primary_raw.metadata.get("quality_report", {}),
            "eastmoney": {
                **(secondary_raw.metadata.get("quality_report", {}) or {}),
                "diagnostics": eastmoney_diagnostics,
            },
        }
        quality_report = build_quality_report(
            symbol=merged.symbol,
            requested_date=trade_date,
            provider=self.provider,
            actual_data_date=(merged.kline_summary or {}).get("actual_data_date"),
            field_values={
                "market_snapshot.close": merged.market_snapshot.get("close"),
                "market_snapshot.pct_change": merged.market_snapshot.get("pct_change"),
                "valuation_raw.pe": merged.valuation_raw.get("pe"),
                "valuation_raw.pb": merged.valuation_raw.get("pb"),
                "financial_raw.roe": merged.financial_raw.get("roe"),
                "financial_raw.net_profit_growth": merged.financial_raw.get("net_profit_growth"),
                "kline_summary.return_20d": merged.kline_summary.get("return_20d"),
                "basic_info.name": merged.basic_info.get("name"),
                "basic_info.industry": merged.basic_info.get("industry"),
                "market_snapshot.turnover_rate": merged.market_snapshot.get("turnover_rate"),
                "market_snapshot.market_cap": merged.market_snapshot.get("market_cap"),
            },
            warnings=merged.metadata.get("data_quality_warnings", []),
            failed_sources=[
                *(primary_raw.metadata.get("failed_sources") or []),
                *(secondary_raw.metadata.get("failed_sources") or []),
            ],
            successful_sources=[
                *(primary_raw.metadata.get("successful_sources") or []),
                *(secondary_raw.metadata.get("successful_sources") or []),
            ],
            field_provenance=merged.metadata.get("field_provenance", {}),
            source_cache_used=[
                *(primary_raw.metadata.get("source_cache_used") or []),
                *(secondary_raw.metadata.get("source_cache_used") or []),
            ],
            live_success_count=(
                (primary_raw.metadata.get("quality_report") or {}).get("live_success_count", 0)
                + (secondary_raw.metadata.get("quality_report") or {}).get("live_success_count", 0)
            ),
            cache_success_count=(
                (primary_raw.metadata.get("quality_report") or {}).get("cache_success_count", 0)
                + (secondary_raw.metadata.get("quality_report") or {}).get("cache_success_count", 0)
            ),
            live_failure_count=(
                (primary_raw.metadata.get("quality_report") or {}).get("live_failure_count", 0)
                + (secondary_raw.metadata.get("quality_report") or {}).get("live_failure_count", 0)
            ),
        )
        merged.metadata["quality_report"] = quality_report.model_dump(mode="json")
        merged.metadata["quality_report"]["providers_used"] = merged.metadata["providers_used"]
        merged.metadata["quality_report"]["provider_reports"] = merged.metadata["provider_reports"]
        merged.metadata["quality_report"]["merge_warnings"] = merged.metadata.get("merge_warnings", [])
        merged.metadata["missing_fields"] = quality_report.missing_fields
        return merged
