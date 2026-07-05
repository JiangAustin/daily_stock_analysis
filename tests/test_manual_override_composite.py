from __future__ import annotations

from pathlib import Path

import pytest

from private_ext.raw_data.models import RawStockData


pytestmark = [pytest.mark.private_ext]


def test_composite_manual_overlay_only_fills_missing_and_respects_allow_override(tmp_path: Path):
    from private_ext.raw_data.composite_collector import CompositeRawDataCollector
    from private_ext.raw_data.manual_override_collector import ManualOverrideRawDataCollector

    class Primary:
        provider = "akshare"

        def collect(self, symbol: str, trade_date: str) -> RawStockData:
            return _raw(close=1500.0, pe=30.0, pb=9.5, roe=None, net_profit_growth=None)

    class Secondary:
        provider = "eastmoney"

        def collect(self, symbol: str, trade_date: str) -> RawStockData:
            return _raw(close=None, pe=None, pb=None, roe=None, net_profit_growth=None)

    manual_dir = tmp_path / "manual_data"
    manual_dir.mkdir()
    (manual_dir / "600519_2026-07-03.csv").write_text(
        "\n".join(
            [
                "field,value,source_note,source_url,updated_at,confidence,allow_override",
                "market_snapshot.close,1600.0,manual close,,2026-07-05,low,false",
                "valuation_raw.pe,18.0,manual pe,,2026-07-05,medium,true",
                "financial_raw.roe,28.0,manual roe,,2026-07-05,medium,false",
            ]
        ),
        encoding="utf-8",
    )

    collector = CompositeRawDataCollector(
        primary=Primary(),
        secondary=Secondary(),
        manual_override=ManualOverrideRawDataCollector(manual_data_dir=manual_dir, file_format="csv", provider_name="manual_csv"),
    )
    raw = collector.collect("600519", "2026-07-03")
    provenance = raw.metadata["field_provenance"]

    assert raw.market_snapshot["close"] == 1500.0
    assert raw.valuation_raw["pe"] == 18.0
    assert raw.financial_raw["roe"] == 28.0
    assert provenance["market_snapshot.close"]["candidate"] == "akshare_snapshot"
    assert provenance["valuation_raw.pe"]["candidate"] == "manual_csv"
    assert provenance["financial_raw.roe"]["candidate"] == "manual_csv"
    assert "manual_override_replaced_live_value:valuation_raw.pe" in raw.metadata["data_quality_warnings"]
    assert "manual_override_filled_missing_field:financial_raw.roe" in raw.metadata["data_quality_warnings"]
    assert raw.metadata["manual_override"]["applied_fields"] == ["valuation_raw.pe", "financial_raw.roe"]
    assert "manual_override" in raw.metadata["provider_reports"]


def _raw(*, close=None, pe=None, pb=None, roe=None, net_profit_growth=None) -> RawStockData:
    return RawStockData(
        symbol="600519",
        trade_date="2026-07-03",
        basic_info={"name": "贵州茅台", "industry": "白酒", "market": "cn"},
        market_snapshot={"close": close, "pct_change": None, "turnover_rate": None, "market_cap": None},
        kline_summary={"return_5d": None, "return_20d": None, "return_60d": None, "actual_data_date": "2026-07-03"},
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
            "provider": "composite",
            "providers_used": ["akshare", "eastmoney"],
            "field_provenance": {
                "market_snapshot.close": {
                    "source": "akshare_snapshot",
                    "candidate": "akshare_snapshot",
                    "fallback_level": 0,
                    "is_cached": False,
                    "confidence": "high",
                },
                "valuation_raw.pe": {
                    "source": "akshare_snapshot",
                    "candidate": "akshare_snapshot",
                    "fallback_level": 0,
                    "is_cached": False,
                    "confidence": "high",
                },
            },
            "quality_report": {
                "provider": "composite",
                "quality_level": "good",
                "warnings": [],
                "missing_fields": [],
                "field_coverage_ratio": 1.0,
                "can_score": True,
                "can_make_decision": True,
                "requested_date": "2026-07-03",
                "actual_data_date": "2026-07-03",
                "critical_fields_present": True,
                "failed_sources": [],
                "successful_sources": ["akshare", "eastmoney"],
                "source_cache_used": [],
                "live_success_count": 2,
                "cache_success_count": 0,
                "live_failure_count": 0,
                "field_provenance_summary": {},
                "symbol": "600519",
                "notes": [],
            },
        },
    )
