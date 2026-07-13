from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from private_ext.raw_data.composite_collector import CompositeRawDataCollector
from private_ext.raw_data.factory import create_raw_data_collector
from private_ext.raw_data.manual_override_collector import ManualOverrideRawDataCollector
from private_ext.raw_data.models import RawStockData


pytestmark = [pytest.mark.private_ext]


def _base_raw(provider: str, close: float | None = 1499.0) -> RawStockData:
    return RawStockData(
        symbol="600519",
        trade_date="2026-07-03",
        basic_info={"name": "贵州茅台", "industry": "白酒"},
        market_snapshot={"close": close, "pct_change": None, "turnover_rate": None, "market_cap": None},
        kline_summary={"return_5d": None, "return_20d": None, "return_60d": None, "actual_data_date": "2026-07-03"},
        valuation_raw={"pe": None, "pb": None},
        financial_raw={"roe": None, "net_profit_growth": None},
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
                    "candidate": f"{provider}_snapshot",
                    "fallback_level": 0,
                    "is_cached": False,
                    "confidence": "high",
                }
            },
            "quality_report": {
                "provider": provider,
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
                "successful_sources": [provider],
                "source_cache_used": [],
                "live_success_count": 1,
                "cache_success_count": 0,
                "live_failure_count": 0,
                "field_provenance_summary": {},
                "symbol": "600519",
                "notes": [],
            },
        },
    )


def _write_manual_csv(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "field",
                "value",
                "source_note",
                "source_url",
                "updated_at",
                "confidence",
                "allow_override",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "field": "market_snapshot.close",
                "value": "1500",
                "source_note": "manual csv close",
                "source_url": "https://example.com/manual-close",
                "updated_at": "2026-07-05",
                "confidence": "high",
                "allow_override": "true",
            }
        )
        writer.writerow(
            {
                "field": "valuation_raw.pe",
                "value": "12.3",
                "source_note": "manual csv pe",
                "source_url": "https://example.com/manual-pe",
                "updated_at": "2026-07-05",
                "confidence": "medium",
                "allow_override": "true",
            }
        )


def _write_manual_json(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            [
                {
                    "field": "market_snapshot.close",
                    "value": 1500,
                    "source_note": "manual json close",
                    "source_url": "https://example.com/manual-close-json",
                    "updated_at": "2026-07-05",
                    "confidence": "medium",
                    "allow_override": True,
                },
                {
                    "field": "valuation_raw.pe",
                    "value": 12.3,
                    "source_note": "manual json pe",
                    "source_url": "https://example.com/manual-pe-json",
                    "updated_at": "2026-07-05",
                    "confidence": "high",
                    "allow_override": True,
                }
            ],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def test_composite_manual_csv_candidate_and_provider_reports(tmp_path: Path):
    manual_dir = tmp_path / "manual_data"
    _write_manual_csv(manual_dir / "600519_2026-07-03.csv")

    collector = CompositeRawDataCollector(
        primary=type("Primary", (), {"provider": "akshare", "collect": lambda self, s, d: _base_raw("akshare", close=1499.0)})(),
        secondary=type("Secondary", (), {"provider": "eastmoney", "collect": lambda self, s, d: _base_raw("eastmoney", close=None)})(),
        manual_override=ManualOverrideRawDataCollector(
            manual_data_dir=manual_dir,
            file_format="auto",
            provider_name="manual_override",
        ),
    )
    raw = collector.collect("600519", "2026-07-03")

    assert raw.metadata["manual_override"]["provider"] == "manual_override"
    assert raw.metadata["manual_override"]["candidate"] == "manual_csv"
    assert raw.metadata["field_provenance"]["market_snapshot.close"]["candidate"] == "manual_csv"
    assert raw.metadata["field_provenance"]["valuation_raw.pe"]["candidate"] == "manual_csv"
    assert raw.metadata["provider_reports"]["manual_override"]["provider"] == "manual_override"
    assert raw.metadata["provider_reports"]["manual_override"]["candidate"] == "manual_csv"


def test_composite_manual_json_candidate_and_provider_reports(tmp_path: Path):
    manual_dir = tmp_path / "manual_data"
    _write_manual_json(manual_dir / "600519_2026-07-03.json")

    collector = CompositeRawDataCollector(
        primary=type("Primary", (), {"provider": "akshare", "collect": lambda self, s, d: _base_raw("akshare", close=1499.0)})(),
        secondary=type("Secondary", (), {"provider": "eastmoney", "collect": lambda self, s, d: _base_raw("eastmoney", close=None)})(),
        manual_override=ManualOverrideRawDataCollector(
            manual_data_dir=manual_dir,
            file_format="auto",
            provider_name="manual_override",
        ),
    )
    raw = collector.collect("600519", "2026-07-03")

    assert raw.metadata["manual_override"]["provider"] == "manual_override"
    assert raw.metadata["manual_override"]["candidate"] == "manual_json"
    assert raw.metadata["field_provenance"]["market_snapshot.close"]["candidate"] == "manual_json"
    assert raw.metadata["field_provenance"]["valuation_raw.pe"]["candidate"] == "manual_json"
    assert raw.metadata["provider_reports"]["manual_override"]["provider"] == "manual_override"
    assert raw.metadata["provider_reports"]["manual_override"]["candidate"] == "manual_json"


def test_factory_creates_manual_collectors(tmp_path: Path):
    manual_dir = tmp_path / "manual_data"
    _write_manual_csv(manual_dir / "600519_2026-07-03.csv")
    _write_manual_json(manual_dir / "600519_2026-07-03.json")

    csv_collector = create_raw_data_collector("manual_csv", manual_data_dir=manual_dir)
    json_collector = create_raw_data_collector("manual_json", manual_data_dir=manual_dir)
    composite_collector = create_raw_data_collector("composite_manual", manual_data_dir=manual_dir, manual_file_format="auto")

    assert csv_collector.provider == "manual_csv"
    assert json_collector.provider == "manual_json"
    assert isinstance(composite_collector, CompositeRawDataCollector)
