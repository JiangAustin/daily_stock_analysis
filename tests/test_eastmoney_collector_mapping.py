from __future__ import annotations

import pytest

from private_ext.fact_pack.builder import FactPackBuilder
from private_ext.raw_data.models import RawStockData


pytestmark = [pytest.mark.private_ext]


def test_eastmoney_collector_maps_fake_payloads_to_raw_stock_data(tmp_path):
    from private_ext.raw_data.eastmoney_collector import EastMoneyRawDataCollector

    collector = EastMoneyRawDataCollector(
        cache_dir=tmp_path,
        use_cache=False,
        refresh=True,
        fetchers={
            "snapshot": lambda symbol: [{"f57": "600519", "f58": "贵州茅台", "f43": 150000, "f170": 125, "f168": 45, "f116": 1900000000000}],
            "valuation": lambda symbol: [{"pe": 24.5, "pb": 8.6}],
            "kline": lambda symbol, trade_date: [
                {"date": f"2026-06-{day:02d}", "close": 1400.0 + day * 4}
                for day in range(1, 26)
            ],
            "financial": lambda symbol: [{"roe": 27.1, "net_profit_growth": 13.8, "report_date": "2026-03-31"}],
        },
    )

    raw = collector.collect("600519", "2026-07-03")

    assert isinstance(raw, RawStockData)
    assert raw.symbol == "600519"
    assert raw.market_snapshot["close"] == 1500.0
    assert raw.market_snapshot["pct_change"] == 0.0125
    assert raw.market_snapshot["turnover_rate"] == 0.45
    assert raw.market_snapshot["market_cap"] == 1900000000000
    assert raw.valuation_raw["pe"] == 24.5
    assert raw.valuation_raw["pb"] == 8.6
    assert raw.kline_summary["return_5d"] is not None
    assert raw.kline_summary["return_20d"] is not None
    assert raw.financial_raw["roe"] == 27.1
    assert raw.financial_raw["net_profit_growth"] == 13.8
    assert raw.metadata["provider"] == "eastmoney"
    assert "quality_report" in raw.metadata
    assert "field_provenance" in raw.metadata
    assert "eastmoney_diagnostics" in raw.metadata
    endpoint_names = [item["endpoint_name"] for item in raw.metadata["eastmoney_diagnostics"]["endpoint_results"]]
    assert endpoint_names == ["snapshot", "valuation", "kline", "financial"]
    assert raw.metadata["eastmoney_diagnostics"]["successful_endpoints"] == [
        "snapshot",
        "valuation",
        "kline",
        "financial",
    ]


def test_eastmoney_collector_gracefully_degrades_when_fields_are_missing(tmp_path):
    from private_ext.raw_data.eastmoney_collector import EastMoneyRawDataCollector

    collector = EastMoneyRawDataCollector(
        cache_dir=tmp_path,
        use_cache=False,
        refresh=True,
        fetchers={
            "snapshot": lambda symbol: [{"f57": "000001", "f58": "平安银行", "f43": 1020}],
            "valuation": lambda symbol: [],
            "kline": lambda symbol, trade_date: [{"date": "2026-07-03", "close": 10.2}],
            "financial": lambda symbol: [],
        },
    )

    raw = collector.collect("000001", "2026-07-03")
    fact_pack = FactPackBuilder().build(raw)

    assert raw.symbol == "000001"
    assert fact_pack.missing_fields
    assert fact_pack.data_quality_warnings
    assert raw.metadata["provider"] == "eastmoney"
    assert raw.metadata["quality_report"]["quality_level"] in {"degraded", "poor", "failed"}
    assert raw.metadata["eastmoney_diagnostics"]["failed_endpoints"] == []
    assert "kline_summary.return_20d" in raw.metadata["eastmoney_diagnostics"]["unresolved_fields"]


def test_eastmoney_collector_uses_kline_for_zero_pct_change_and_records_provenance(tmp_path):
    from private_ext.raw_data.eastmoney_collector import EastMoneyRawDataCollector

    collector = EastMoneyRawDataCollector(
        cache_dir=tmp_path,
        use_cache=False,
        refresh=True,
        fetchers={
            "snapshot": lambda symbol: [{"f57": "600519", "f58": "贵州茅台"}],
            "valuation": lambda symbol: [],
            "kline": lambda symbol, trade_date: [
                {"date": "2026-06-30", "close": 10.0},
                {"date": "2026-07-01", "close": 10.0},
                {"date": "2026-07-02", "close": 10.0},
                {"date": "2026-07-03", "close": 10.0},
                {"date": "2026-07-04", "close": 10.0},
                {"date": "2026-07-05", "close": 10.0},
            ],
            "financial": lambda symbol: [],
        },
    )

    raw = collector.collect("600519", "2026-07-03")
    provenance = raw.metadata["field_provenance"]

    assert raw.market_snapshot["pct_change"] == 0.0
    assert provenance["market_snapshot.pct_change"]["source"] == "eastmoney_kline"
    assert provenance["market_snapshot.pct_change"]["is_cached"] is False
    assert raw.kline_summary["return_20d"] is None


def test_eastmoney_collector_retries_then_uses_source_cache_and_records_diagnostics(tmp_path):
    from private_ext.raw_data.cache import RawDataCache
    from private_ext.raw_data.eastmoney_collector import EastMoneyRawDataCollector

    cache = RawDataCache(tmp_path)
    cache.write_source(
        "eastmoney",
        "eastmoney_push2_snapshot",
        "600519",
        "2026-07-03",
        [{"f57": "600519", "f58": "贵州茅台", "f43": 150000, "f170": 125, "f168": 45, "f116": 1900000000000}],
    )
    attempts = {"snapshot": 0}

    def failing_snapshot(symbol):
        attempts["snapshot"] += 1
        raise RuntimeError("RemoteDisconnected")

    collector = EastMoneyRawDataCollector(
        cache_dir=tmp_path,
        use_cache=True,
        refresh=False,
        fetchers={
            "eastmoney_push2_snapshot": failing_snapshot,
            "eastmoney_quote_snapshot_fallback": failing_snapshot,
            "valuation": lambda symbol: [],
            "kline": lambda symbol, trade_date: [],
            "financial": lambda symbol: [],
        },
    )

    raw = collector.collect("600519", "2026-07-03")
    diagnostics = raw.metadata["eastmoney_diagnostics"]
    snapshot_result = next(
        item for item in diagnostics["candidate_results"] if item["candidate_name"] == "eastmoney_push2_snapshot"
    )

    assert attempts["snapshot"] == 2
    assert raw.market_snapshot["close"] == 1500.0
    assert snapshot_result["status"] == "cache"
    assert snapshot_result["used_cache"] is True
    assert snapshot_result["error_type"] == "RuntimeError"
    assert "eastmoney_push2_snapshot" in diagnostics["cache_used"]
    assert raw.metadata["field_provenance"]["market_snapshot.close"]["is_cached"] is True
    assert raw.metadata["field_provenance"]["market_snapshot.close"]["source"] == "eastmoney_snapshot"


def test_eastmoney_collector_marks_insufficient_kline_window(tmp_path):
    from private_ext.raw_data.eastmoney_collector import EastMoneyRawDataCollector

    collector = EastMoneyRawDataCollector(
        cache_dir=tmp_path,
        use_cache=False,
        refresh=True,
        fetchers={
            "snapshot": lambda symbol: [{"f57": "600519", "f58": "贵州茅台", "f43": 150000, "f170": 125}],
            "valuation": lambda symbol: [],
            "kline": lambda symbol, trade_date: [
                {"date": "2026-07-01", "close": 1490.0},
                {"date": "2026-07-02", "close": 1495.0},
                {"date": "2026-07-03", "close": 1500.0},
            ],
            "financial": lambda symbol: [],
        },
    )

    raw = collector.collect("600519", "2026-07-03")

    assert raw.kline_summary["return_20d"] is None
    assert "eastmoney_insufficient_kline_window_for_return_20d" in raw.metadata["data_quality_warnings"]
    assert raw.kline_summary["return_available_window"] == 2
