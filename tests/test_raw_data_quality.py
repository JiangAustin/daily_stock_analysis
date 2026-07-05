from private_ext.raw_data.quality import RawDataQualityReport, build_quality_report


def test_quality_report_classifies_good_when_core_fields_are_present():
    report = build_quality_report(
        symbol="600519",
        requested_date="2026-07-03",
        provider="akshare",
        actual_data_date="2026-07-03",
        field_values={
            "market_snapshot.close": 1500.0,
            "market_snapshot.pct_change": 1.2,
            "valuation_raw.pe": 24.0,
            "valuation_raw.pb": 8.5,
            "financial_raw.roe": 27.0,
            "financial_raw.net_profit_growth": 14.0,
            "kline_summary.return_20d": 6.2,
            "financial_raw.net_margin": 51.0,
            "capital_flow_raw.main_net_inflow": 200000000.0,
        },
        warnings=[],
        failed_sources=[],
        successful_sources=["spot", "hist", "financial"],
    )

    assert isinstance(report, RawDataQualityReport)
    assert report.quality_level == "good"
    assert report.can_score is True
    assert report.can_make_decision is True


def test_quality_report_classifies_degraded_when_critical_fields_are_missing():
    report = build_quality_report(
        symbol="600519",
        requested_date="2026-07-03",
        provider="akshare",
        actual_data_date=None,
        field_values={
            "market_snapshot.close": None,
            "market_snapshot.pct_change": 1.2,
            "valuation_raw.pe": None,
            "valuation_raw.pb": 8.5,
            "financial_raw.roe": 27.0,
            "financial_raw.net_profit_growth": 14.0,
            "kline_summary.return_20d": 6.2,
        },
        warnings=["spot_failed:ProxyError"],
        failed_sources=["spot"],
        successful_sources=["financial"],
    )

    assert report.quality_level in {"degraded", "poor"}
    assert "market_snapshot.close" in report.missing_fields
    assert report.can_make_decision is False


def test_quality_report_classifies_failed_when_coverage_is_too_low():
    report = build_quality_report(
        symbol="600519",
        requested_date="2026-07-03",
        provider="akshare",
        actual_data_date=None,
        field_values={
            "market_snapshot.close": None,
            "market_snapshot.pct_change": None,
            "valuation_raw.pe": None,
            "valuation_raw.pb": None,
            "financial_raw.roe": None,
            "financial_raw.net_profit_growth": None,
            "kline_summary.return_20d": None,
        },
        warnings=["spot_failed:ProxyError", "hist_failed:ProxyError"],
        failed_sources=["spot", "hist"],
        successful_sources=[],
    )

    assert report.quality_level == "failed"
    assert report.can_score is False
    assert report.can_make_decision is False
