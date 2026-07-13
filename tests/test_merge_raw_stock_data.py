from __future__ import annotations

import math

import pytest

from private_ext.raw_data.models import RawStockData


pytestmark = [pytest.mark.private_ext]


def _raw(
    *,
    provider: str,
    close=None,
    pct_change=None,
    turnover_rate=None,
    market_cap=None,
    pe=None,
    pb=None,
    roe=None,
    net_profit_growth=None,
    return_5d=None,
    return_20d=None,
    return_60d=None,
    field_provenance: dict[str, dict[str, object]] | None = None,
    quality_level: str = "degraded",
    extra_warnings: list[str] | None = None,
) -> RawStockData:
    return RawStockData(
        symbol="600519",
        trade_date="2026-07-03",
        basic_info={"name": "贵州茅台", "industry": "白酒", "market": "cn"},
        market_snapshot={
            "close": close,
            "pct_change": pct_change,
            "turnover_rate": turnover_rate,
            "market_cap": market_cap,
        },
        kline_summary={
            "return_5d": return_5d,
            "return_20d": return_20d,
            "return_60d": return_60d,
            "actual_data_date": "2026-07-03",
        },
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
            "field_provenance": field_provenance or {},
            "quality_report": {
                "provider": provider,
                "quality_level": quality_level,
                "warnings": list(extra_warnings or []),
                "missing_fields": [],
                "field_coverage_ratio": 0.7,
                "can_score": True,
                "can_make_decision": provider != "broken",
                "requested_date": "2026-07-03",
                "actual_data_date": "2026-07-03",
                "critical_fields_present": True,
                "failed_sources": [],
                "successful_sources": [provider],
                "source_cache_used": [],
                "live_success_count": 1,
                "cache_success_count": 0,
                "live_failure_count": 0,
                "field_provenance_summary": field_provenance or {},
                "symbol": "600519",
                "notes": [],
            },
            "data_quality_warnings": list(extra_warnings or []),
        },
    )


def _prov(source: str, *, is_cached: bool = False, confidence: str = "high", fallback_level: int = 0):
    return {
        "source": source,
        "is_cached": is_cached,
        "confidence": confidence,
        "fallback_level": fallback_level,
    }


def test_merge_uses_secondary_when_primary_fields_are_missing():
    from private_ext.raw_data.merge import merge_raw_stock_data

    primary = _raw(provider="akshare", close=None, return_20d=None, field_provenance={})
    secondary = _raw(
        provider="eastmoney",
        close=1501.0,
        return_20d=0.12,
        field_provenance={
            "market_snapshot.close": _prov("eastmoney_snapshot"),
            "kline_summary.return_20d": _prov("eastmoney_kline"),
        },
    )

    merged = merge_raw_stock_data(primary, secondary)

    assert merged.market_snapshot["close"] == 1501.0
    assert merged.kline_summary["return_20d"] == 0.12
    assert merged.metadata["field_provenance"]["market_snapshot.close"]["source"] == "eastmoney_snapshot"


def test_merge_keeps_primary_when_primary_is_high_confidence():
    from private_ext.raw_data.merge import merge_raw_stock_data

    primary = _raw(
        provider="akshare",
        close=1500.0,
        field_provenance={"market_snapshot.close": _prov("stock_zh_a_spot_em", confidence="high")},
    )
    secondary = _raw(
        provider="eastmoney",
        close=1501.0,
        field_provenance={"market_snapshot.close": _prov("eastmoney_snapshot", confidence="high")},
    )

    merged = merge_raw_stock_data(primary, secondary)

    assert merged.market_snapshot["close"] == 1500.0
    assert merged.metadata["field_provenance"]["market_snapshot.close"]["source"] == "stock_zh_a_spot_em"


def test_merge_allows_live_secondary_to_override_cached_primary():
    from private_ext.raw_data.merge import merge_raw_stock_data

    primary = _raw(
        provider="akshare",
        close=1498.0,
        field_provenance={"market_snapshot.close": _prov("raw_cache", is_cached=True, confidence="medium", fallback_level=2)},
    )
    secondary = _raw(
        provider="eastmoney",
        close=1501.0,
        field_provenance={"market_snapshot.close": _prov("eastmoney_snapshot", confidence="high")},
    )

    merged = merge_raw_stock_data(primary, secondary)

    assert merged.market_snapshot["close"] == 1501.0
    assert merged.metadata["field_provenance"]["market_snapshot.close"]["source"] == "eastmoney_snapshot"


@pytest.mark.parametrize(
    ("field_name", "primary_kwargs", "secondary_kwargs", "warning"),
    [
        (
            "close",
            {"close": 100.0, "field_provenance": {"market_snapshot.close": _prov("stock_zh_a_spot_em")}},
            {"close": 104.0, "field_provenance": {"market_snapshot.close": _prov("eastmoney_snapshot")}},
            "provider_value_conflict:market_snapshot.close",
        ),
        (
            "pct_change",
            {"pct_change": 0.01, "field_provenance": {"market_snapshot.pct_change": _prov("stock_zh_a_spot_em")}},
            {"pct_change": 0.05, "field_provenance": {"market_snapshot.pct_change": _prov("eastmoney_snapshot")}},
            "provider_value_conflict:market_snapshot.pct_change",
        ),
        (
            "pe",
            {"pe": 20.0, "field_provenance": {"valuation_raw.pe": _prov("stock_zh_a_spot_em")}},
            {"pe": 23.0, "field_provenance": {"valuation_raw.pe": _prov("eastmoney_valuation")}},
            "provider_value_conflict:valuation_raw.pe",
        ),
        (
            "pb",
            {"pb": 2.0, "field_provenance": {"valuation_raw.pb": _prov("stock_zh_a_spot_em")}},
            {"pb": 2.4, "field_provenance": {"valuation_raw.pb": _prov("eastmoney_valuation")}},
            "provider_value_conflict:valuation_raw.pb",
        ),
        (
            "return_20d",
            {"return_20d": 0.10, "field_provenance": {"kline_summary.return_20d": _prov("stock_zh_a_hist")}},
            {"return_20d": 0.18, "field_provenance": {"kline_summary.return_20d": _prov("eastmoney_kline")}},
            "provider_value_conflict:kline_summary.return_20d",
        ),
    ],
)
def test_merge_records_conflicts_when_provider_values_diverge(field_name, primary_kwargs, secondary_kwargs, warning):
    from private_ext.raw_data.merge import merge_raw_stock_data

    primary = _raw(provider="akshare", **primary_kwargs)
    secondary = _raw(provider="eastmoney", **secondary_kwargs)

    merged = merge_raw_stock_data(primary, secondary)

    assert warning in merged.metadata["merge_warnings"]
    if field_name == "close":
        assert merged.market_snapshot["close"] == 100.0
    if field_name == "pct_change":
        assert merged.market_snapshot["pct_change"] == 0.01
    if field_name == "pe":
        assert merged.valuation_raw["pe"] == 20.0
    if field_name == "pb":
        assert merged.valuation_raw["pb"] == 2.0
    if field_name == "return_20d":
        assert merged.kline_summary["return_20d"] == 0.10


def test_merge_treats_nan_and_na_as_missing():
    from private_ext.raw_data.merge import merge_raw_stock_data

    primary = _raw(
        provider="akshare",
        close=math.nan,
        pe="N/A",
        field_provenance={
            "market_snapshot.close": _prov("stock_zh_a_spot_em"),
            "valuation_raw.pe": _prov("stock_zh_a_spot_em"),
        },
    )
    secondary = _raw(
        provider="eastmoney",
        close=1500.0,
        pe=24.0,
        field_provenance={
            "market_snapshot.close": _prov("eastmoney_snapshot"),
            "valuation_raw.pe": _prov("eastmoney_valuation"),
        },
    )

    merged = merge_raw_stock_data(primary, secondary)

    assert merged.market_snapshot["close"] == 1500.0
    assert merged.valuation_raw["pe"] == 24.0


def test_merge_accumulates_metadata_and_provenance():
    from private_ext.raw_data.merge import merge_raw_stock_data

    primary = _raw(
        provider="akshare",
        close=1500.0,
        extra_warnings=["akshare_warning"],
        field_provenance={"market_snapshot.close": _prov("stock_zh_a_spot_em")},
    )
    secondary = _raw(
        provider="eastmoney",
        return_20d=0.15,
        extra_warnings=["eastmoney_warning"],
        field_provenance={"kline_summary.return_20d": _prov("eastmoney_kline")},
    )

    merged = merge_raw_stock_data(primary, secondary)

    assert merged.metadata["providers_used"] == ["akshare", "eastmoney"]
    assert "akshare" in merged.metadata["provider_reports"]
    assert "eastmoney" in merged.metadata["provider_reports"]
    assert merged.metadata["field_provenance"]["market_snapshot.close"]["source"] == "stock_zh_a_spot_em"
    assert merged.metadata["field_provenance"]["kline_summary.return_20d"]["source"] == "eastmoney_kline"
