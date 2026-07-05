import pytest

from private_ext.raw_data.akshare_fallbacks import (
    fill_kline_summary,
    fill_market_snapshot,
    fill_valuation,
)

pytestmark = pytest.mark.private_ext


def _safe_float(value):
    return None if value in (None, "", "-", "--") else float(value)


def test_fill_market_snapshot_falls_back_to_hist_and_cache():
    summary = {
        "latest_close": 1502.0,
        "latest_pct_change": 0.13,
        "return_20d": 5.8,
    }
    snapshot, provenance, warnings = fill_market_snapshot(
        spot_row={},
        info_map={},
        hist_summary=summary,
        source_context={"stock_zh_a_hist": {"is_cached": False}},
        cached_raw={"market_snapshot": {"turnover_rate": 0.48, "market_cap": 1900000000000.0}},
        as_float=_safe_float,
    )

    assert snapshot["close"] == 1502.0
    assert snapshot["pct_change"] == 0.13
    assert snapshot["turnover_rate"] == 0.48
    assert snapshot["market_cap"] == 1900000000000.0
    assert provenance["market_snapshot.close"]["source"] == "stock_zh_a_hist"
    assert provenance["market_snapshot.close"]["fallback_level"] == 1
    assert provenance["market_snapshot.turnover_rate"]["source"] == "raw_cache"
    assert provenance["market_snapshot.turnover_rate"]["is_cached"] is True
    assert warnings == []


def test_fill_kline_summary_marks_insufficient_return20d_window_and_preserves_hist_provenance():
    records = [
        {"日期": "2026-07-01", "收盘": 10.0},
        {"日期": "2026-07-02", "收盘": 10.5},
        {"日期": "2026-07-03", "收盘": 11.0},
    ]

    summary, provenance, warnings = fill_kline_summary(
        hist_records=records,
        source_context={"stock_zh_a_hist": {"is_cached": False}},
        cached_raw=None,
        as_float=_safe_float,
    )

    assert summary["return_5d"] is None
    assert summary["return_20d"] is None
    assert provenance["kline_summary.return_20d"]["source"] is None
    assert provenance["kline_summary.return_20d"]["confidence"] == "missing"
    assert "return_20d_unavailable_after_hist_fallbacks" in warnings


def test_fill_valuation_falls_back_to_info_map_when_spot_missing():
    valuation, provenance, warnings = fill_valuation(
        spot_row={},
        info_map={"市盈率": "24.6", "市净率": "8.1"},
        financial_row={},
        source_context={"stock_individual_info_em": {"is_cached": False}},
        cached_raw=None,
        as_float=_safe_float,
    )

    assert valuation["pe"] == 24.6
    assert valuation["pb"] == 8.1
    assert provenance["valuation_raw.pe"]["source"] == "stock_individual_info_em"
    assert provenance["valuation_raw.pe"]["fallback_level"] == 1
    assert warnings == []
