from __future__ import annotations

import json
from pathlib import Path

import pytest

from private_ext.raw_data.manual_override import apply_manual_override
from private_ext.raw_data.models import RawStockData


pytestmark = [pytest.mark.private_ext]


def test_manual_override_factory_and_collector_parse_csv_and_json(tmp_path: Path):
    from private_ext.raw_data.factory import create_raw_data_collector

    manual_dir = tmp_path / "manual_data"
    manual_dir.mkdir()
    csv_path = manual_dir / "600519_2026-07-03.csv"
    csv_path.write_text(
        "\n".join(
            [
                "field,value,source_note,source_url,updated_at,confidence,allow_override",
                "market_snapshot.close,1600.0,manual research,,2026-07-05,high,false",
                "valuation_raw.pe,0.0,manual research,,2026-07-05,,false",
            ]
        ),
        encoding="utf-8",
    )

    collector = create_raw_data_collector("manual_csv", manual_data_dir=manual_dir)
    raw = collector.collect("600519", "2026-07-03")
    provenance = raw.metadata["field_provenance"]

    assert raw.metadata["provider"] == "manual_csv"
    assert raw.market_snapshot["close"] == 1600.0
    assert provenance["market_snapshot.close"]["source"] == "manual_override"
    assert provenance["market_snapshot.close"]["candidate"] == "manual_csv"
    assert provenance["market_snapshot.close"]["confidence"] == "high"
    assert provenance["market_snapshot.close"]["source_note"] == "manual research"
    assert provenance["market_snapshot.close"]["updated_at"] == "2026-07-05"
    assert raw.valuation_raw["pe"] == 0.0
    assert provenance["valuation_raw.pe"]["confidence"] == "medium"
    assert "manual_override_filled_missing_field:market_snapshot.close" in raw.metadata["data_quality_warnings"]
    assert "manual_override_filled_missing_field:valuation_raw.pe" in raw.metadata["data_quality_warnings"]

    json_path = manual_dir / "600519_2026-07-03.json"
    json_path.write_text(
        json.dumps(
            [
                {
                    "field": "market_snapshot.pct_change",
                    "value": 0.0,
                    "source_note": "json manual",
                    "source_url": "https://example.invalid/manual",
                    "updated_at": "2026-07-05",
                    "confidence": "low",
                    "allow_override": True,
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    json_collector = create_raw_data_collector("manual_json", manual_data_dir=manual_dir)
    json_raw = json_collector.collect("600519", "2026-07-03")
    assert json_raw.market_snapshot["pct_change"] == 0.0
    assert json_raw.metadata["field_provenance"]["market_snapshot.pct_change"]["candidate"] == "manual_json"
    assert json_raw.metadata["field_provenance"]["market_snapshot.pct_change"]["confidence"] == "low"


def test_manual_override_only_replaces_live_values_when_explicitly_allowed():
    base_raw = _base_raw(close=1500.0, pe=30.0, pb=9.5)
    manual_raw = RawStockData(
        symbol="600519",
        trade_date="2026-07-03",
        basic_info={},
        market_snapshot={"close": 1600.0},
        kline_summary={},
        valuation_raw={
            "pe": 18.0,
            "pb": 7.5,
        },
        financial_raw={"roe": 28.0, "net_profit_growth": 12.0},
        capital_flow_raw={},
        northbound_raw={},
        dragon_tiger_raw={},
        announcements_raw=[],
        news_raw=[],
        analyst_raw=[],
        industry_raw={},
        metadata={
            "provider": "manual_csv",
            "manual_override": {
                "provider": "manual_csv",
                "source_path": "storage/manual_data/600519_2026-07-03.csv",
                "records": [
                    {
                        "field": "market_snapshot.close",
                        "value": 1600.0,
                        "source_note": "manual close",
                        "source_url": None,
                        "updated_at": "2026-07-05",
                        "confidence": "low",
                        "allow_override": False,
                    },
                    {
                        "field": "valuation_raw.pe",
                        "value": 18.0,
                        "source_note": "manual pe",
                        "source_url": None,
                        "updated_at": "2026-07-05",
                        "confidence": "medium",
                        "allow_override": True,
                    },
                    {
                        "field": "financial_raw.roe",
                        "value": 28.0,
                        "source_note": "manual roe",
                        "source_url": None,
                        "updated_at": "2026-07-05",
                        "confidence": "medium",
                        "allow_override": False,
                    },
                ],
                "applied_records": [],
                "skipped_records": [],
            },
        },
    )

    merged = apply_manual_override(
        base_raw,
        [
            _record("market_snapshot.close", 1600.0, "manual close", "2026-07-05", "low", False),
            _record("valuation_raw.pe", 18.0, "manual pe", "2026-07-05", "medium", True),
            _record("financial_raw.roe", 28.0, "manual roe", "2026-07-05", "medium", False),
        ],
        candidate="manual_csv",
        source_path="storage/manual_data/600519_2026-07-03.csv",
        required=False,
    )

    assert merged.market_snapshot["close"] == 1500.0
    assert merged.valuation_raw["pe"] == 18.0
    assert merged.financial_raw["roe"] == 28.0
    assert "manual_override_replaced_live_value:valuation_raw.pe" in merged.metadata["data_quality_warnings"]
    assert "manual_override_filled_missing_field:financial_raw.roe" in merged.metadata["data_quality_warnings"]
    assert merged.metadata["field_provenance"]["valuation_raw.pe"]["candidate"] == "manual_csv"
    assert merged.metadata["field_provenance"]["valuation_raw.pe"]["allow_override"] is True


def test_check_realdata_health_verbose_prints_manual_override(monkeypatch, capsys):
    import scripts.check_realdata_health as health

    class FakeCollector:
        def collect(self, symbol: str, trade_date: str):
            return _base_raw(
                close=1500.0,
                pe=30.0,
                pb=9.5,
                manual_override={
                    "provider": "manual_csv",
                    "source_path": "storage/manual_data/600519_2026-07-03.csv",
                    "records": [],
                    "applied_records": [
                        {
                            "field": "valuation_raw.pe",
                            "value": 18.0,
                            "source_note": "manual pe",
                            "source_url": None,
                            "updated_at": "2026-07-05",
                            "confidence": "low",
                            "allow_override": True,
                            "applied": True,
                            "action": "replaced_live",
                        }
                    ],
                    "skipped_records": [],
                    "applied_fields": ["valuation_raw.pe"],
                    "filled_missing_fields": [],
                    "replaced_live_fields": ["valuation_raw.pe"],
                    "warnings": ["manual_override_replaced_live_value:valuation_raw.pe"],
                },
            )

    monkeypatch.setattr(health, "create_raw_data_collector", lambda *args, **kwargs: FakeCollector())
    code = health.main(["--stocks", "600519", "--raw-data", "manual_csv", "--verbose"])
    out = capsys.readouterr().out

    assert code == 0
    assert "manual_override:" in out
    assert "valuation_raw.pe" in out


def _base_raw(*, close=None, pe=None, pb=None, manual_override=None) -> RawStockData:
    metadata = {
        "provider": "composite",
        "providers_used": ["akshare", "eastmoney"],
        "field_provenance": {},
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
    }
    if manual_override is not None:
        metadata["manual_override"] = manual_override
        metadata["quality_report"]["manual_override"] = manual_override
    return RawStockData(
        symbol="600519",
        trade_date="2026-07-03",
        basic_info={"name": "贵州茅台", "industry": "白酒", "market": "cn"},
        market_snapshot={"close": close, "pct_change": None, "turnover_rate": None, "market_cap": None},
        kline_summary={"return_5d": None, "return_20d": None, "return_60d": None, "actual_data_date": "2026-07-03"},
        valuation_raw={"pe": pe, "pb": pb},
        financial_raw={"roe": None, "net_profit_growth": None},
        capital_flow_raw={},
        northbound_raw={},
        dragon_tiger_raw={},
        announcements_raw=[],
        news_raw=[],
        analyst_raw=[],
        industry_raw={},
        metadata=metadata,
    )


def _record(field: str, value: object, source_note: str, updated_at: str, confidence: str, allow_override: bool):
    return type(
        "ManualRecord",
        (),
        {
            "field": field,
            "value": value,
            "source_note": source_note,
            "source_url": None,
            "updated_at": updated_at,
            "confidence": confidence,
            "allow_override": allow_override,
            "as_dict": lambda self=None: {
                "field": field,
                "value": value,
                "source_note": source_note,
                "source_url": None,
                "updated_at": updated_at,
                "confidence": confidence,
                "allow_override": allow_override,
            },
        },
    )()
