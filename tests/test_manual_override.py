from __future__ import annotations

import csv
from pathlib import Path

import pytest

from private_ext.raw_data.factory import create_raw_data_collector


pytestmark = [pytest.mark.private_ext]


def _write_manual_csv(path: Path, *, close: str = "1500", allow_override: str = "false") -> None:
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
                "value": close,
                "source_note": "manual csv close",
                "source_url": "https://example.com/manual-close",
                "updated_at": "2026-07-05",
                "confidence": "high",
                "allow_override": allow_override,
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
                "allow_override": allow_override,
            }
        )


def _write_manual_json(path: Path, *, close: str = "1500", allow_override: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        __import__("json").dumps(
            [
                {
                    "field": "market_snapshot.close",
                    "value": close,
                    "source_note": "manual json close",
                    "source_url": "https://example.com/manual-close-json",
                    "updated_at": "2026-07-05",
                    "confidence": "medium",
                    "allow_override": allow_override,
                },
                {
                    "field": "valuation_raw.pe",
                    "value": 12.3,
                    "source_note": "manual json pe",
                    "source_url": "https://example.com/manual-pe-json",
                    "updated_at": "2026-07-05",
                    "confidence": "high",
                    "allow_override": allow_override,
                }
            ],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def test_manual_csv_provider_preserves_provider_and_candidate(tmp_path: Path):
    manual_dir = tmp_path / "manual_data"
    _write_manual_csv(manual_dir / "600519_2026-07-03.csv")

    collector = create_raw_data_collector("manual_csv", manual_data_dir=manual_dir)
    raw = collector.collect("600519", "2026-07-03")

    assert raw.metadata["provider"] == "manual_csv"
    assert raw.metadata["manual_override"]["provider"] == "manual_csv"
    assert raw.metadata["manual_override"]["candidate"] == "manual_csv"
    assert raw.metadata["field_provenance"]["market_snapshot.close"]["candidate"] == "manual_csv"
    assert raw.metadata["field_provenance"]["valuation_raw.pe"]["candidate"] == "manual_csv"


def test_manual_json_provider_preserves_provider_and_candidate(tmp_path: Path):
    manual_dir = tmp_path / "manual_data"
    _write_manual_json(manual_dir / "600519_2026-07-03.json")

    collector = create_raw_data_collector("manual_json", manual_data_dir=manual_dir)
    raw = collector.collect("600519", "2026-07-03")

    assert raw.metadata["provider"] == "manual_json"
    assert raw.metadata["manual_override"]["provider"] == "manual_json"
    assert raw.metadata["manual_override"]["candidate"] == "manual_json"
    assert raw.metadata["field_provenance"]["market_snapshot.close"]["candidate"] == "manual_json"
    assert raw.metadata["field_provenance"]["valuation_raw.pe"]["candidate"] == "manual_json"
