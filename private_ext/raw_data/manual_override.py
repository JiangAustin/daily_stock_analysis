from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from private_ext.raw_data.models import RawStockData


SUPPORTED_FIELDS = {
    "market_snapshot.close",
    "market_snapshot.pct_change",
    "kline_summary.return_5d",
    "kline_summary.return_20d",
    "kline_summary.return_60d",
    "valuation_raw.pe",
    "valuation_raw.pb",
    "financial_raw.roe",
    "financial_raw.net_profit_growth",
}


@dataclass(slots=True)
class ManualOverrideRecord:
    field: str
    value: Any
    source_note: str | None
    source_url: str | None
    updated_at: str | None
    confidence: str
    allow_override: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "field": self.field,
            "value": self.value,
            "source_note": self.source_note,
            "source_url": self.source_url,
            "updated_at": self.updated_at,
            "confidence": self.confidence,
            "allow_override": self.allow_override,
        }


def first_non_missing(*values: Any) -> Any:
    for value in values:
        if not _is_missing(value):
            return value
    return None


def manual_override_path(manual_data_dir: str | Path, symbol: str, trade_date: str, file_format: str) -> Path:
    ext = {"csv": "csv", "json": "json"}.get(file_format, file_format)
    return Path(manual_data_dir) / f"{symbol}_{trade_date}.{ext}"


def load_manual_override_records(
    *,
    manual_data_dir: str | Path,
    symbol: str,
    trade_date: str,
    file_format: str = "auto",
) -> tuple[list[ManualOverrideRecord], str, Path]:
    if file_format not in {"auto", "csv", "json"}:
        raise ValueError("manual_file_format must be auto, csv, or json")

    csv_path = manual_override_path(manual_data_dir, symbol, trade_date, "csv")
    json_path = manual_override_path(manual_data_dir, symbol, trade_date, "json")
    if file_format == "auto":
        if csv_path.exists():
            return _load_manual_override_csv(csv_path), "manual_csv", csv_path
        if json_path.exists():
            return _load_manual_override_json(json_path), "manual_json", json_path
        raise FileNotFoundError(
            f"No manual override file found for {symbol} {trade_date} under {manual_data_dir}"
        )
    if file_format == "csv":
        if not csv_path.exists():
            raise FileNotFoundError(f"Manual CSV file not found: {csv_path}")
        return _load_manual_override_csv(csv_path), "manual_csv", csv_path
    if not json_path.exists():
        raise FileNotFoundError(f"Manual JSON file not found: {json_path}")
    return _load_manual_override_json(json_path), "manual_json", json_path


def build_manual_raw_stock_data(
    *,
    symbol: str,
    trade_date: str,
    records: list[ManualOverrideRecord],
    provider: str,
    candidate: str,
    source_path: str | Path,
) -> RawStockData:
    base = RawStockData(
        symbol=symbol,
        trade_date=trade_date,
        basic_info={},
        market_snapshot={},
        kline_summary={},
        valuation_raw={},
        financial_raw={},
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
            "manual_override": {
                "provider": provider,
                "candidate": candidate,
                "source_path": str(source_path),
                "records": [record.as_dict() for record in records],
                "applied_records": [],
                "skipped_records": [],
                "applied_fields": [],
                "filled_missing_fields": [],
                "replaced_live_fields": [],
            },
            "data_quality_warnings": [],
            "field_provenance": {},
        },
    )
    return apply_manual_override_to_raw(base, manual_raw=base)


def apply_manual_override_to_raw(base_raw: RawStockData, *, manual_raw: RawStockData) -> RawStockData:
    merged = base_raw.model_dump(mode="json")
    manual_meta = dict((manual_raw.metadata or {}).get("manual_override") or {})
    provider = first_non_missing(manual_meta.get("provider"), manual_raw.metadata.get("provider"), "manual_override")
    candidate = first_non_missing(
        manual_meta.get("candidate"),
        manual_meta.get("provider"),
        manual_raw.metadata.get("provider"),
        "manual_override",
    )
    records = _normalize_records(manual_meta.get("records", []))

    provenance = dict((merged.get("metadata") or {}).get("field_provenance") or {})
    warnings = list((merged.get("metadata") or {}).get("data_quality_warnings") or [])
    applied_records: list[dict[str, Any]] = []
    skipped_records: list[dict[str, Any]] = []
    applied_fields: list[str] = []
    filled_missing_fields: list[str] = []
    replaced_live_fields: list[str] = []

    for record in records:
        current_value = _get_nested(merged, record.field)
        if _is_missing(current_value) or record.allow_override:
            if _is_missing(current_value):
                filled_missing_fields.append(record.field)
                warnings.append(f"manual_override_filled_missing_field:{record.field}")
            else:
                replaced_live_fields.append(record.field)
                warnings.append(f"manual_override_replaced_live_value:{record.field}")
            _set_nested(merged, record.field, record.value)
            provenance[record.field] = {
                "source": provider,
                "candidate": candidate,
                "is_cached": False,
                "confidence": record.confidence,
                "source_note": record.source_note,
                "source_url": record.source_url,
                "updated_at": record.updated_at,
                "allow_override": record.allow_override,
            }
            applied_records.append(record.as_dict())
            applied_fields.append(record.field)
        else:
            skipped_records.append(record.as_dict())

    merged_metadata = dict(merged.get("metadata") or {})
    merged_metadata["provider"] = merged_metadata.get("provider", provider)
    merged_metadata["providers_used"] = _unique_list([*(merged_metadata.get("providers_used") or []), provider])
    merged_metadata["manual_override"] = {
        **manual_meta,
        "provider": provider,
        "candidate": candidate,
        "records": [record.as_dict() for record in records],
        "applied_records": applied_records,
        "skipped_records": skipped_records,
        "applied_fields": applied_fields,
        "filled_missing_fields": filled_missing_fields,
        "replaced_live_fields": replaced_live_fields,
    }
    merged_metadata["data_quality_warnings"] = _unique_list([*warnings])
    merged_metadata["field_provenance"] = provenance
    merged["metadata"] = merged_metadata
    return RawStockData.model_validate(merged)


def _load_manual_override_csv(path: Path) -> list[ManualOverrideRecord]:
    rows: list[ManualOverrideRecord] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows.append(_record_from_dict(row))
    return rows


def _load_manual_override_json(path: Path) -> list[ManualOverrideRecord]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"Manual JSON file must contain a list of records: {path}")
    return [_record_from_dict(item) for item in payload]


def _record_from_dict(data: dict[str, Any]) -> ManualOverrideRecord:
    field = str(data.get("field", "")).strip()
    if not field:
        raise ValueError("Manual override record is missing field")
    if field not in SUPPORTED_FIELDS:
        raise ValueError(f"Unsupported manual override field: {field}")
    confidence = str(data.get("confidence") or "medium").strip().lower()
    if confidence not in {"low", "medium", "high"}:
        confidence = "medium"
    allow_override = str(data.get("allow_override", "")).strip().lower() in {"1", "true", "yes", "on"}
    return ManualOverrideRecord(
        field=field,
        value=_parse_value(data.get("value")),
        source_note=_string_or_none(data.get("source_note")),
        source_url=_string_or_none(data.get("source_url")),
        updated_at=_string_or_none(data.get("updated_at")),
        confidence=confidence,
        allow_override=allow_override,
    )


def _parse_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (int, float, bool)):
        return value
    text = str(value).strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        return text


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_records(records: list[dict[str, Any]] | list[ManualOverrideRecord]) -> list[ManualOverrideRecord]:
    normalized: list[ManualOverrideRecord] = []
    for record in records:
        if isinstance(record, ManualOverrideRecord):
            normalized.append(record)
        else:
            normalized.append(_record_from_dict(record))
    return normalized


def _get_nested(payload: dict[str, Any], path: str) -> Any:
    current: Any = payload
    for part in path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def _set_nested(payload: dict[str, Any], path: str, value: Any) -> None:
    current = payload
    parts = path.split(".")
    for part in parts[:-1]:
        current = current.setdefault(part, {})
    current[parts[-1]] = value


def _is_missing(value: Any) -> bool:
    if value in (None, "", "-", "--", "N/A", "n/a", [], {}):
        return True
    return isinstance(value, float) and math.isnan(value)


def _unique_list(values: list[Any]) -> list[Any]:
    seen: list[Any] = []
    for value in values:
        if value not in seen:
            seen.append(value)
    return seen
