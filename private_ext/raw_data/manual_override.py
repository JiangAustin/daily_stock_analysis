from __future__ import annotations

from dataclasses import dataclass
import csv
import json
from pathlib import Path
from typing import Any, Iterable

from private_ext.raw_data.akshare_fallbacks import build_field_provenance, summarize_field_provenance
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

NUMERIC_FIELDS = SUPPORTED_FIELDS
ALLOWED_CONFIDENCE = {"low", "medium", "high"}


@dataclass(frozen=True)
class ManualOverrideRecord:
    field: str
    value: Any
    source_note: str
    source_url: str | None
    updated_at: str
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


def manual_override_path(manual_data_dir: Path, symbol: str, trade_date: str, file_format: str) -> Path:
    suffix = file_format.lower().strip()
    if suffix not in {"csv", "json"}:
        raise ValueError(f"Unsupported manual override format: {file_format}")
    return manual_data_dir / f"{symbol}_{trade_date}.{suffix}"


def load_manual_override_records(
    *,
    manual_data_dir: Path,
    symbol: str,
    trade_date: str,
    file_format: str = "auto",
) -> tuple[list[ManualOverrideRecord], Path | None, str]:
    manual_data_dir = Path(manual_data_dir)
    candidates = _candidate_paths(manual_data_dir, symbol, trade_date, file_format)
    for path, candidate_name in candidates:
        if not path.exists():
            continue
        if path.suffix.lower() == ".csv":
            return _parse_manual_csv(path), path, candidate_name
        if path.suffix.lower() == ".json":
            return _parse_manual_json(path), path, candidate_name
        raise ValueError(f"Unsupported manual override file suffix: {path.suffix}")
    return [], None, _candidate_name_for_format(file_format)


def apply_manual_override(
    base_raw: RawStockData,
    records: Iterable[ManualOverrideRecord],
    *,
    candidate: str,
    source_path: str | None,
    required: bool = True,
) -> RawStockData:
    payload = base_raw.model_dump(mode="json")
    metadata = dict(payload.get("metadata") or {})
    warnings = list(dict.fromkeys(str(item) for item in metadata.get("data_quality_warnings", []) if item))
    manual_records = [record.as_dict() for record in records]
    applied_records: list[dict[str, Any]] = []
    skipped_records: list[dict[str, Any]] = []
    field_provenance = dict(metadata.get("field_provenance") or {})

    for record in records:
        if record.field not in SUPPORTED_FIELDS:
            warnings.append(f"manual_override_unknown_field:{record.field}")
            skipped_records.append({**record.as_dict(), "applied": False, "reason": "unknown_field"})
            continue
        if _is_missing(record.value):
            warnings.append(f"manual_override_missing_value:{record.field}")
            skipped_records.append({**record.as_dict(), "applied": False, "reason": "missing_value"})
            continue

        current_value = _get_nested(payload, record.field)
        if _is_missing(current_value):
            _set_nested(payload, record.field, record.value)
            warnings.append(f"manual_override_filled_missing_field:{record.field}")
            applied_records.append({**record.as_dict(), "applied": True, "action": "filled_missing"})
            field_provenance[record.field] = build_field_provenance(
                source="manual_override",
                candidate=candidate,
                fallback_level=0,
                is_cached=False,
                confidence=record.confidence,
                source_note=record.source_note,
                source_url=record.source_url,
                updated_at=record.updated_at,
                allow_override=record.allow_override,
            )
            continue

        if record.allow_override:
            _set_nested(payload, record.field, record.value)
            warnings.append(f"manual_override_replaced_live_value:{record.field}")
            applied_records.append({**record.as_dict(), "applied": True, "action": "replaced_live"})
            field_provenance[record.field] = build_field_provenance(
                source="manual_override",
                candidate=candidate,
                fallback_level=0,
                is_cached=False,
                confidence=record.confidence,
                source_note=record.source_note,
                source_url=record.source_url,
                updated_at=record.updated_at,
                allow_override=record.allow_override,
            )
            continue

        skipped_records.append({**record.as_dict(), "applied": False, "reason": "live_value_present"})

    metadata["field_provenance"] = summarize_field_provenance(field_provenance)
    manual_override = {
        "provider": candidate,
        "source_path": source_path,
        "records": manual_records,
        "applied_records": applied_records,
        "skipped_records": skipped_records,
        "applied_fields": [item["field"] for item in applied_records],
        "filled_missing_fields": [item["field"] for item in applied_records if item.get("action") == "filled_missing"],
        "replaced_live_fields": [item["field"] for item in applied_records if item.get("action") == "replaced_live"],
        "warnings": warnings,
    }
    metadata["manual_override"] = manual_override
    metadata["data_quality_warnings"] = sorted(set(warnings))
    if required and source_path is None:
        raise FileNotFoundError(f"Manual override file not found for {base_raw.symbol} on {base_raw.trade_date}")
    payload["metadata"] = metadata
    return RawStockData.model_validate(payload)


def build_manual_raw_stock_data(
    *,
    symbol: str,
    trade_date: str,
    records: Iterable[ManualOverrideRecord],
    candidate: str,
    source_path: str | None,
) -> RawStockData:
    payload = {
        "symbol": symbol,
        "trade_date": trade_date,
        "basic_info": {},
        "market_snapshot": {"currency": "CNY"},
        "kline_summary": {},
        "valuation_raw": {},
        "financial_raw": {},
        "capital_flow_raw": {},
        "northbound_raw": {},
        "dragon_tiger_raw": {},
        "announcements_raw": [],
        "news_raw": [],
        "analyst_raw": [],
        "industry_raw": {},
        "metadata": {},
    }
    manual_raw = RawStockData.model_validate(payload)
    manual_override = apply_manual_override(
        manual_raw,
        records,
        candidate=candidate,
        source_path=source_path,
        required=False,
    )
    manual_override.metadata["manual_override"]["records"] = [record.as_dict() for record in records]
    return manual_override


def _parse_manual_csv(path: Path) -> list[ManualOverrideRecord]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return [_row_to_record(row) for row in rows]


def _parse_manual_json(path: Path) -> list[ManualOverrideRecord]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"Manual override JSON must contain an array: {path}")
    return [_row_to_record(row) for row in data if isinstance(row, dict)]


def _row_to_record(row: dict[str, Any]) -> ManualOverrideRecord:
    field = str(row.get("field", "")).strip()
    if not field:
        raise ValueError("Manual override record is missing field")
    value = _coerce_value(field, row.get("value"))
    source_note = str(row.get("source_note", "")).strip()
    source_url = _string_or_none(row.get("source_url"))
    updated_at = str(row.get("updated_at", "")).strip()
    confidence = str(row.get("confidence", "medium")).strip().lower() or "medium"
    if confidence not in ALLOWED_CONFIDENCE:
        confidence = "medium"
    allow_override = _coerce_bool(row.get("allow_override", False))
    return ManualOverrideRecord(
        field=field,
        value=value,
        source_note=source_note,
        source_url=source_url,
        updated_at=updated_at,
        confidence=confidence,
        allow_override=allow_override,
    )


def _coerce_value(field: str, value: Any) -> Any:
    if field in NUMERIC_FIELDS:
        if _is_missing(value):
            return None
        if isinstance(value, (int, float)):
            return float(value)
        text = str(value).strip()
        if not text:
            return None
        try:
            return float(text)
        except ValueError:
            return value
    return value


def _candidate_paths(manual_data_dir: Path, symbol: str, trade_date: str, file_format: str) -> list[tuple[Path, str]]:
    if file_format == "auto":
        return [
            (manual_override_path(manual_data_dir, symbol, trade_date, "csv"), "manual_csv"),
            (manual_override_path(manual_data_dir, symbol, trade_date, "json"), "manual_json"),
        ]
    candidate = f"manual_{file_format.lower().strip()}"
    return [(manual_override_path(manual_data_dir, symbol, trade_date, file_format), candidate)]


def _candidate_name_for_format(file_format: str) -> str:
    if file_format == "auto":
        return "manual_override"
    return f"manual_{file_format.lower().strip()}"


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    return text in {"1", "true", "yes", "y", "on"}


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _get_nested(payload: dict[str, Any], path: str) -> Any:
    current: Any = payload
    for part in path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def _set_nested(payload: dict[str, Any], path: str, value: Any) -> None:
    parts = path.split(".")
    current = payload
    for part in parts[:-1]:
        current = current.setdefault(part, {})
    current[parts[-1]] = value


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float):
        return value != value
    if isinstance(value, str):
        return value.strip() in {"", "-", "N/A", "n/a", "--"}
    return value in ([], {})
