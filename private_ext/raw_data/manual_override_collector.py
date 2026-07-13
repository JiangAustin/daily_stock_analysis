from __future__ import annotations

from pathlib import Path
from typing import Any

from private_ext.raw_data.base import RawDataCollector
from private_ext.raw_data.manual_override import (
    apply_manual_override_to_raw,
    build_manual_raw_stock_data,
    load_manual_override_records,
)
from private_ext.raw_data.models import RawStockData


class ManualOverrideRawDataCollector(RawDataCollector):
    def __init__(
        self,
        *,
        manual_data_dir: str | Path,
        file_format: str = "auto",
        provider_name: str = "manual_override",
        required: bool = True,
        **_: Any,
    ) -> None:
        self.manual_data_dir = Path(manual_data_dir)
        self.file_format = file_format
        self.provider = provider_name
        self.required = required

    def collect(self, symbol: str, trade_date: str) -> RawStockData:
        records, candidate, source_path = load_manual_override_records(
            manual_data_dir=self.manual_data_dir,
            symbol=symbol,
            trade_date=trade_date,
            file_format=self.file_format,
        )
        manual_raw = build_manual_raw_stock_data(
            symbol=symbol,
            trade_date=trade_date,
            records=records,
            provider=self.provider,
            candidate=candidate,
            source_path=source_path,
        )
        manual_raw.metadata["manual_override"]["provider"] = self.provider
        if not manual_raw.metadata["manual_override"].get("candidate"):
            manual_raw.metadata["manual_override"]["candidate"] = candidate or self.provider
        manual_raw.metadata["manual_override"]["source_path"] = str(source_path)
        manual_raw.metadata["provider"] = self.provider
        manual_raw.metadata["providers_used"] = [self.provider]
        manual_raw.metadata["quality_report"] = {
            "provider": self.provider,
            "candidate": candidate,
            "manual_override": manual_raw.metadata["manual_override"],
            "quality_level": "good",
            "warnings": [],
            "missing_fields": [],
            "field_coverage_ratio": 1.0,
            "can_score": True,
            "can_make_decision": True,
            "requested_date": trade_date,
            "actual_data_date": trade_date,
            "critical_fields_present": True,
            "failed_sources": [],
            "successful_sources": [self.provider],
            "source_cache_used": [],
            "live_success_count": 0,
            "cache_success_count": 0,
            "live_failure_count": 0,
            "field_provenance_summary": manual_raw.metadata.get("field_provenance", {}),
            "symbol": symbol,
            "notes": [],
        }
        return manual_raw
