from __future__ import annotations

from pathlib import Path
from typing import Any

from private_ext.config import settings
from private_ext.raw_data.base import RawDataCollector
from private_ext.raw_data.manual_override import (
    apply_manual_override,
    build_manual_raw_stock_data,
    load_manual_override_records,
)
from private_ext.raw_data.models import RawStockData
from private_ext.raw_data.quality import build_quality_report


class ManualOverrideRawDataCollector(RawDataCollector):
    def __init__(
        self,
        *,
        manual_data_dir: Path | None = None,
        file_format: str = "csv",
        provider_name: str | None = None,
        required: bool = True,
        **kwargs,
    ):
        self.manual_data_dir = Path(manual_data_dir or settings.storage_dir / "manual_data")
        self.file_format = file_format
        self.provider = provider_name or f"manual_{file_format}"
        self.required = required
        self._ignored_kwargs = dict(kwargs)

    def collect(self, symbol: str, trade_date: str) -> RawStockData:
        records, source_path, candidate = load_manual_override_records(
            manual_data_dir=self.manual_data_dir,
            symbol=symbol,
            trade_date=trade_date,
            file_format=self.file_format,
        )
        if not records and self.required:
            path_hint = source_path or self._fallback_path(symbol, trade_date)
            raise FileNotFoundError(f"Manual override file not found: {path_hint}")

        raw = build_manual_raw_stock_data(
            symbol=symbol,
            trade_date=trade_date,
            records=records,
            candidate=candidate,
            source_path=str(source_path) if source_path else None,
        )
        raw.metadata["provider"] = self.provider
        raw.metadata["providers_used"] = [self.provider]
        raw.metadata["manual_override"]["provider"] = self.provider
        raw.metadata["manual_override"]["source_path"] = str(source_path) if source_path else None
        raw.metadata["manual_override"]["warnings"] = list(dict.fromkeys(raw.metadata.get("data_quality_warnings", [])))
        raw.metadata["requested_date"] = trade_date
        raw.metadata["actual_data_date"] = trade_date
        raw.metadata["source_cache_used"] = []
        raw.metadata["failed_sources"] = []
        raw.metadata["successful_sources"] = [self.provider]
        quality_report = build_quality_report(
            symbol=symbol,
            requested_date=trade_date,
            provider=self.provider,
            actual_data_date=trade_date,
            field_values=_manual_field_values(raw),
            warnings=raw.metadata.get("data_quality_warnings", []),
            failed_sources=[],
            successful_sources=[self.provider],
            field_provenance=raw.metadata.get("field_provenance", {}),
            source_cache_used=[],
            live_success_count=0,
            cache_success_count=0,
            live_failure_count=0,
        )
        raw.metadata["quality_report"] = quality_report.model_dump(mode="json")
        raw.metadata["quality_report"]["manual_override"] = raw.metadata.get("manual_override", {})
        raw.metadata["missing_fields"] = quality_report.missing_fields
        raw.metadata["manual_override"]["quality_level"] = quality_report.quality_level
        raw.metadata["manual_override"]["applied_fields"] = raw.metadata["manual_override"].get("applied_fields", [])
        return raw

    def _fallback_path(self, symbol: str, trade_date: str) -> Path:
        suffix = "json" if self.file_format == "auto" else self.file_format
        return self.manual_data_dir / f"{symbol}_{trade_date}.{suffix}"


def apply_manual_override_to_raw(
    base_raw: RawStockData,
    *,
    manual_raw: RawStockData,
) -> RawStockData:
    override = manual_raw.metadata.get("manual_override", {}) if isinstance(manual_raw.metadata, dict) else {}
    records = override.get("records", []) if isinstance(override, dict) else []
    candidate = override.get("provider", manual_raw.metadata.get("provider", "manual_override"))
    source_path = override.get("source_path")
    if not records:
        return base_raw
    return apply_manual_override(
        base_raw,
        [_record_from_dict(item) for item in records if isinstance(item, dict)],
        candidate=candidate,
        source_path=source_path,
        required=False,
    )


def _record_from_dict(item: dict[str, Any]):
    from private_ext.raw_data.manual_override import ManualOverrideRecord
    from private_ext.raw_data.manual_override import _string_or_none

    return ManualOverrideRecord(
        field=str(item.get("field", "")).strip(),
        value=item.get("value"),
        source_note=str(item.get("source_note", "")).strip(),
        source_url=_string_or_none(item.get("source_url")),
        updated_at=str(item.get("updated_at", "")).strip(),
        confidence=str(item.get("confidence", "medium")).strip().lower() or "medium",
        allow_override=bool(item.get("allow_override", False)),
    )


def _manual_field_values(raw: RawStockData) -> dict[str, Any]:
    return {
        "market_snapshot.close": (raw.market_snapshot or {}).get("close"),
        "market_snapshot.pct_change": (raw.market_snapshot or {}).get("pct_change"),
        "valuation_raw.pe": (raw.valuation_raw or {}).get("pe"),
        "valuation_raw.pb": (raw.valuation_raw or {}).get("pb"),
        "financial_raw.roe": (raw.financial_raw or {}).get("roe"),
        "financial_raw.net_profit_growth": (raw.financial_raw or {}).get("net_profit_growth"),
        "kline_summary.return_20d": (raw.kline_summary or {}).get("return_20d"),
        "kline_summary.return_5d": (raw.kline_summary or {}).get("return_5d"),
        "kline_summary.return_60d": (raw.kline_summary or {}).get("return_60d"),
    }
