from __future__ import annotations

import pytest

from private_ext.raw_data.akshare_kline import (
    build_akshare_symbol_candidates,
    compute_kline_returns,
    extract_latest_close_and_pct_change,
    normalize_a_share_symbol,
)


pytestmark = pytest.mark.private_ext


def test_normalize_a_share_symbol_handles_common_variants():
    assert normalize_a_share_symbol("600519") == "600519"
    assert normalize_a_share_symbol("sh600519") == "600519"
    assert normalize_a_share_symbol("600519.SH") == "600519"
    assert normalize_a_share_symbol("000001.SZ") == "000001"


def test_build_akshare_symbol_candidates_returns_prefixed_and_plain_codes():
    candidates = build_akshare_symbol_candidates("600519.SH")

    assert candidates[0] == "600519"
    assert "sh600519" in candidates


def test_compute_kline_returns_calculates_available_windows_as_decimal_ratios():
    rows = []
    close = 10.0
    for day in range(25):
        rows.append({"日期": f"2026-06-{day + 1:02d}", "收盘": close})
        close += 1.0

    summary = compute_kline_returns(rows)

    assert summary["latest_close"] == 34.0
    assert summary["return_5d"] == pytest.approx(5 / 29, rel=1e-6)
    assert summary["return_20d"] == pytest.approx(20 / 14, rel=1e-6)
    assert summary["warnings"] == []


def test_compute_kline_returns_reports_insufficient_window_warning():
    rows = [
        {"日期": "2026-07-01", "收盘": 10.0},
        {"日期": "2026-07-02", "收盘": 11.0},
        {"日期": "2026-07-03", "收盘": 12.0},
        {"日期": "2026-07-04", "收盘": 13.0},
        {"日期": "2026-07-05", "收盘": 14.0},
        {"日期": "2026-07-06", "收盘": 15.0},
    ]

    summary = compute_kline_returns(rows)

    assert summary["return_5d"] == pytest.approx(0.5, rel=1e-6)
    assert summary["return_20d"] is None
    assert "insufficient_kline_window_for_return_20d" in summary["warnings"]


def test_extract_latest_close_and_pct_change_from_chinese_columns():
    result = extract_latest_close_and_pct_change(
        [
            {"日期": "2026-07-02", "收盘": 10.0},
            {"日期": "2026-07-03", "收盘": 10.5},
        ]
    )

    assert result["latest_close"] == 10.5
    assert result["latest_pct_change"] == pytest.approx(0.05, rel=1e-6)
    assert result["actual_data_date"] == "2026-07-03"


def test_extract_latest_close_and_pct_change_empty_rows_do_not_crash():
    result = extract_latest_close_and_pct_change([])

    assert result["latest_close"] is None
    assert result["latest_pct_change"] is None
    assert result["actual_data_date"] is None
