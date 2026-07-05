from __future__ import annotations

import pytest

from private_ext.raw_data.models import RawStockData


pytestmark = [pytest.mark.private_ext]


def _raw(
    provider: str,
    *,
    close=None,
    return_20d=None,
    pe=None,
    pb=None,
    roe=None,
    net_profit_growth=None,
) -> RawStockData:
    return RawStockData(
        symbol="600519",
        trade_date="2026-07-03",
        basic_info={"name": "贵州茅台", "industry": "白酒", "market": "cn"},
        market_snapshot={"close": close, "pct_change": None, "turnover_rate": None, "market_cap": None},
        kline_summary={"return_5d": None, "return_20d": return_20d, "return_60d": None, "actual_data_date": "2026-07-03"},
        valuation_raw={"pe": pe, "pb": pb},
        financial_raw={"roe": roe, "net_profit_growth": net_profit_growth},
        capital_flow_raw={},
        northbound_raw={},
        dragon_tiger_raw={},
        announcements_raw=[],
        news_raw=[],
        analyst_raw=[],
        industry_raw={},
        metadata={
            "provider": provider,
            "providers_used": [provider],
            "field_provenance": {
                "market_snapshot.close": {
                    "source": f"{provider}_snapshot",
                    "fallback_level": 0,
                    "is_cached": False,
                    "confidence": "high" if close is not None else "missing",
                },
                "kline_summary.return_20d": {
                    "source": f"{provider}_kline",
                    "fallback_level": 0,
                    "is_cached": False,
                    "confidence": "high" if return_20d is not None else "missing",
                },
            },
            "quality_report": {
                "provider": provider,
                "quality_level": "degraded",
                "warnings": [],
                "missing_fields": [],
                "field_coverage_ratio": 0.6,
                "can_score": True,
                "can_make_decision": close is not None,
                "requested_date": "2026-07-03",
                "actual_data_date": "2026-07-03",
                "critical_fields_present": close is not None,
                "failed_sources": [],
                "successful_sources": [provider],
                "source_cache_used": [],
                "live_success_count": 1,
                "cache_success_count": 0,
                "live_failure_count": 0,
                "field_provenance_summary": {},
                "symbol": "600519",
                "notes": [],
            },
            "eastmoney_diagnostics": {
                "symbol": "600519",
                "requested_date": "2026-07-03",
                "endpoint_results": [
                    {
                        "endpoint_name": "snapshot",
                        "purpose": "market snapshot",
                        "status": "success",
                        "error_type": None,
                        "error_message": None,
                        "elapsed_ms": 1,
                        "target_fields": ["close"],
                        "fields_found": ["close"],
                        "fields_missing": [],
                        "used_cache": False,
                        "raw_sample_path": None,
                        "notes": [],
                    }
                ] if provider == "eastmoney" else [],
                "successful_endpoints": ["snapshot"] if provider == "eastmoney" else [],
                "failed_endpoints": [],
                "fields_filled_by_endpoint": {"snapshot": ["close"]} if provider == "eastmoney" else {},
                "unresolved_fields": [],
                "remote_errors": [],
                "cache_used": [],
                "notes": [],
            },
        },
    )


def test_composite_collector_merges_primary_and_secondary():
    from private_ext.raw_data.composite_collector import CompositeRawDataCollector

    class Primary:
        provider = "akshare"

        def collect(self, symbol: str, trade_date: str) -> RawStockData:
            return _raw("akshare", close=1500.0, return_20d=None, pe=24.0)

    class Secondary:
        provider = "eastmoney"

        def collect(self, symbol: str, trade_date: str) -> RawStockData:
            return _raw("eastmoney", close=None, return_20d=0.12, pe=24.2)

    collector = CompositeRawDataCollector(primary=Primary(), secondary=Secondary())
    raw = collector.collect("600519", "2026-07-03")

    assert isinstance(raw, RawStockData)
    assert raw.market_snapshot["close"] == 1500.0
    assert raw.kline_summary["return_20d"] == 0.12
    assert raw.metadata["provider"] == "composite"
    assert raw.metadata["providers_used"] == ["akshare", "eastmoney"]
    assert "akshare" in raw.metadata["provider_reports"]
    assert "eastmoney" in raw.metadata["provider_reports"]
    assert "quality_report" in raw.metadata
    assert "diagnostics" in raw.metadata["provider_reports"]["eastmoney"]
    assert raw.metadata["quality_report"]["provider_reports"]["eastmoney"]["diagnostics"]["successful_endpoints"] == ["snapshot"]
    assert raw.metadata["field_provenance"]["market_snapshot.close"]["source"] == "akshare_snapshot"
    assert raw.metadata["field_provenance"]["kline_summary.return_20d"]["source"] == "eastmoney_kline"


def test_factory_creates_eastmoney_and_composite_collectors():
    from private_ext.raw_data.composite_collector import CompositeRawDataCollector
    from private_ext.raw_data.eastmoney_collector import EastMoneyRawDataCollector
    from private_ext.raw_data.factory import create_raw_data_collector

    assert isinstance(create_raw_data_collector("eastmoney"), EastMoneyRawDataCollector)
    assert isinstance(create_raw_data_collector("composite"), CompositeRawDataCollector)
